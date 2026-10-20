"""Configurable reference tariffs. Distances are straight-line estimates, NOT road routes."""
from decimal import Decimal, ROUND_HALF_UP
from math import radians, sin, cos, asin, sqrt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Tariff, Service, User
from app.schemas import Kind, ServiceType, TariffIn, TariffOut, PriceEstimateOut
from app.security import require_roles
from app.events import publish

router=APIRouter(prefix='/tariffs', tags=['Tarifas orientativas'])
DELIVERY={ServiceType.parcel,ServiceType.scheduled_route}

def kind_of(value:ServiceType): return Kind.delivery if value in DELIVERY else Kind.roadside

def haversine_km(lat1,lng1,lat2,lng2):
    lat1,lng1,lat2,lng2=map(lambda x:radians(float(x)),[lat1,lng1,lat2,lng2])
    delta_lat=lat2-lat1;delta_lng=lng2-lng1
    a=sin(delta_lat/2)**2+cos(lat1)*cos(lat2)*sin(delta_lng/2)**2
    return Decimal(str(6371.0088*2*asin(min(1,sqrt(a)))))

def money(value): return value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)

@router.get('',response_model=list[TariffOut])
def list_tariffs(db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    return db.scalars(select(Tariff).where(Tariff.company_id==actor.company_id).order_by(Tariff.service_type)).all()

@router.put('/{service_type}',response_model=TariffOut)
def update_tariff(service_type:ServiceType,data:TariffIn,db:Session=Depends(get_db),actor:User=Depends(require_roles('admin'))):
    if service_type != data.service_type:
        raise HTTPException(422,detail='El tipo de tarifa debe coincidir con la URL')
    tariff=db.scalar(select(Tariff).where(Tariff.company_id==actor.company_id,Tariff.service_type==service_type.value))
    if tariff is None:
        tariff=Tariff(company_id=actor.company_id,kind=kind_of(service_type).value,service_type=service_type.value,
                      base_dop=data.base_dop,per_km_dop=data.per_km_dop,minimum_dop=data.minimum_dop,
                      operator_base_dop=data.operator_base_dop,active=data.active,updated_by=actor.id)
        db.add(tariff)
    else:
        for key,val in data.model_dump().items():
            if key!='service_type': setattr(tariff,key,val)
        tariff.updated_by=actor.id
    db.flush();publish(db,actor.company_id,'tariff_changed',tariff.id);db.commit();db.refresh(tariff)
    return tariff

@router.get('/estimate/{service_id}',response_model=PriceEstimateOut)
def estimate(service_id:int,db:Session=Depends(get_db),actor:User=Depends(require_roles('admin','dispatcher'))):
    svc=db.scalar(select(Service).where(Service.company_id==actor.company_id,Service.id==service_id))
    if svc is None: raise HTTPException(404,detail='Solicitud no encontrada')
    t=db.scalar(select(Tariff).where(Tariff.company_id==actor.company_id,
               Tariff.service_type==svc.service_type,Tariff.active.is_(True)))
    if t is None: raise HTTPException(404,detail='No existe tarifa activa para este tipo de servicio')
    d=None
    if None not in (svc.lat,svc.lng,svc.destination_lat,svc.destination_lng):
        d=haversine_km(svc.lat,svc.lng,svc.destination_lat,svc.destination_lng)
    elif t.per_km_dop>0:
        raise HTTPException(422,detail='Para tarifa por kilómetro se requieren coordenadas verificadas de origen y destino')
    base=t.base_dop+(t.per_km_dop*(d or Decimal('0')))
    total=money(max(t.minimum_dop,base))
    return PriceEstimateOut(service_type=svc.service_type,mode='straight_line_estimate' if d is not None else 'base_only',
           distance_km=money(d) if d is not None else None,suggested_total_dop=total,
           suggested_operator_fee_dop=min(t.operator_base_dop,total),
           warning='Estimación orientativa, no utiliza rutas viales ni tráfico. Despacho debe confirmar el precio final antes de aceptar.')
