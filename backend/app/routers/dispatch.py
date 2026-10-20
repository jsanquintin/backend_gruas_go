"""Authenticated dispatcher SSE and GPS tracking. No third-party map provider required."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, asin, sqrt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session, sessionmaker
from app.db import get_db
from app.models import DispatchEvent, Operator, OperatorLocation, Service, User
from app.schemas import LocationIn, OperatorPositionOut
from app.security import current_user, require_roles
from app.routers.operators import documents_valid
from app.events import publish

router = APIRouter(prefix='/dispatch', tags=['Despacho GPS y eventos'])
ACTIVE = ('assigned','en_route','on_site')
FRESH_SECONDS=180

def current_positions(db: Session, company_id: int):
    latest = (select(OperatorLocation.operator_id,func.max(OperatorLocation.id).label('latest_id'))
              .where(OperatorLocation.company_id==company_id).group_by(OperatorLocation.operator_id).subquery())
    rows = db.execute(select(Operator,OperatorLocation)
                      .join(latest,latest.c.operator_id==Operator.id)
                      .join(OperatorLocation,OperatorLocation.id==latest.c.latest_id)
                      .where(Operator.company_id==company_id)).all()
    now=datetime.now(timezone.utc)
    active=set(db.scalars(select(Service.operator_id).where(Service.company_id==company_id,
                      Service.status.in_(ACTIVE),Service.operator_id.is_not(None))).all())
    result=[]
    for op,pos in rows:
        recorded=pos.recorded_at.replace(tzinfo=timezone.utc) if pos.recorded_at.tzinfo is None else pos.recorded_at
        online=(now-recorded).total_seconds()<=FRESH_SECONDS
        result.append(OperatorPositionOut(operator_id=op.id,name=op.name,kind=op.kind,
            lat=pos.lat,lng=pos.lng,accuracy_m=pos.accuracy_m,recorded_at=recorded,
            online=online,available=bool(online and op.active and op.verified and
                    op.verification_status=='approved' and documents_valid(op) and op.id not in active)))
    return result

@router.post('/my-location',status_code=201)
def publish_my_location(data: LocationIn,db: Session=Depends(get_db),actor:User=Depends(require_roles('driver'))):
    op=db.scalar(select(Operator).where(Operator.company_id==actor.company_id,Operator.user_id==actor.id))
    if not op or not op.active or not op.verified or op.verification_status!='approved' or not documents_valid(op):
        raise HTTPException(status_code=403,detail='Conductor sin operador aprobado y activo asociado')
    # No falsificamos GPS: posición declarada por el dispositivo, sin garantía de autenticidad.
    row=OperatorLocation(company_id=actor.company_id,operator_id=op.id,lat=data.lat,lng=data.lng,
                         accuracy_m=data.accuracy_m)
    db.add(row);db.flush()
    publish(db,actor.company_id,'operator_location',op.id)
    # Mantener últimas 50 lecturas por operador; no geolocalización indefinida.
    stale_ids=db.scalars(select(OperatorLocation.id).where(OperatorLocation.operator_id==op.id)
                         .order_by(OperatorLocation.id.desc()).offset(50)).all()
    if stale_ids:
        from sqlalchemy import delete
        db.execute(delete(OperatorLocation).where(OperatorLocation.id.in_(stale_ids)))
    db.commit()
    return {'operator_id':op.id,'recorded_at':row.recorded_at,'message':'Ubicación recibida'}

@router.get('/positions',response_model=list[OperatorPositionOut])
def positions(db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    return current_positions(db,actor.company_id)

@router.get('/updates')
def updates(since:int=0,db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    if since<0: raise HTTPException(422,detail='Cursor inválido')
    rows=db.scalars(select(DispatchEvent).where(DispatchEvent.company_id==actor.company_id,
               DispatchEvent.id>since).order_by(DispatchEvent.id).limit(100)).all()
    latest=db.scalar(select(func.max(DispatchEvent.id)).where(DispatchEvent.company_id==actor.company_id)) or 0
    return {'cursor':max(since, max([x.id for x in rows],default=0)),
            'latest':latest,
            'events':[{'id':x.id,'kind':x.kind,'ref_id':x.ref_id} for x in rows]}

@router.get('/stream')
async def stream(request:Request, db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    # Sigue el número de eventos por compañía; sin contenido de clientes en el SSE.
    company_id=actor.company_id
    bind=db.get_bind()
    local=sessionmaker(bind=bind,expire_on_commit=False)
    async def events():
        connected_at=datetime.now(timezone.utc)
        with local() as session:
            cursor=session.scalar(select(func.max(DispatchEvent.id)).where(DispatchEvent.company_id==company_id)) or 0
        yield ': conectado\n\n'
        # Limitar cada conexion obliga a revalidar el JWT periodicamente.
        while ((datetime.now(timezone.utc)-connected_at).total_seconds()<50
               and not await request.is_disconnected()):
            await asyncio.sleep(2)
            with local() as session:
                batch=session.scalars(select(DispatchEvent).where(DispatchEvent.company_id==company_id,
                       DispatchEvent.id>cursor).order_by(DispatchEvent.id).limit(100)).all()
            for item in batch:
                cursor=item.id
                payload=json.dumps({'id':item.id,'kind':item.kind,'ref_id':item.ref_id})
                yield f'id: {item.id}\nevent: update\ndata: {payload}\n\n'
            if not batch: yield ': latido\n\n'
    return StreamingResponse(events(),media_type='text/event-stream',headers={
        'Cache-Control':'no-cache, no-transform','X-Accel-Buffering':'no'})


@router.get('/candidates/{service_id}')
def nearest_candidates(service_id:int,db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    svc=db.scalar(select(Service).where(Service.id==service_id,Service.company_id==actor.company_id))
    if not svc: raise HTTPException(404,detail='Solicitud no encontrada')
    ranked=[]
    for pos in current_positions(db,actor.company_id):
        if not pos.available or pos.kind.value!=svc.kind:continue
        distance=None
        if svc.lat is not None and svc.lng is not None:
            la1,lo1,la2,lo2=map(lambda n:radians(float(n)),(svc.lat,svc.lng,pos.lat,pos.lng))
            a=sin((la2-la1)/2)**2+cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
            distance=round(6371.0088*2*asin(min(1,sqrt(a))),2)
        ranked.append({'operator_id':pos.operator_id,'name':pos.name,'kind':pos.kind,
               'distance_straight_km':distance,'accuracy_m':pos.accuracy_m,
               'recorded_at':pos.recorded_at})
    ranked.sort(key=lambda x: (x['distance_straight_km'] is None,
                                 x['distance_straight_km'] if x['distance_straight_km'] is not None else 0))
    return {'candidates':ranked,'warning':'Distancias rectas, no tiempos estimados de llegada. Despacho confirma la asignación.'}
