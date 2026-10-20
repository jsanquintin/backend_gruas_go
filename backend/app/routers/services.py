from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.db import get_db
from app.models import Operator, Service, ServiceEvent, User
from app.schemas import AssignmentIn, Kind, ServiceIn, ServiceOut, Status, StatusIn, QuoteIn
from app.security import current_user, require_roles
from app.routers.operators import documents_valid
from app.events import publish

router = APIRouter(prefix='/services', tags=['Solicitudes'])
ALLOWED = {
    'pending': {'assigned', 'canceled'},
    'assigned': {'en_route', 'canceled'},
    'en_route': {'on_site', 'completed', 'canceled'},
    'on_site': {'completed', 'canceled'},
    'completed': set(), 'canceled': set(),
}

def accessible_query(user: User):
    q = select(Service).options(selectinload(Service.events)).where(Service.company_id == user.company_id)
    if user.role == 'merchant':
        q = q.where(Service.created_by == user.id)
    elif user.role == 'driver':
        q = q.join(Operator, Service.operator_id == Operator.id).where(Operator.user_id == user.id)
    return q

def get_accessible(db: Session, actor: User, service_id: int) -> Service:
    obj = db.scalar(accessible_query(actor).where(Service.id == service_id))
    if obj is None:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    return obj

def add_event(db: Session, service: Service, actor: User, name: str, detail: str):
    db.add(ServiceEvent(service_id=service.id, actor_id=actor.id, event_type=name, detail=detail))

@router.get('', response_model=list[ServiceOut])
def list_services(kind: Kind | None = None, status: Status | None = None, limit: int = Query(default=100, ge=1, le=300), db: Session = Depends(get_db), actor: User = Depends(current_user)):
    q = accessible_query(actor)
    if kind: q = q.where(Service.kind == kind.value)
    if status: q = q.where(Service.status == status.value)
    return db.scalars(q.order_by(Service.id.desc()).limit(limit)).all()

@router.post('', response_model=ServiceOut, status_code=201)
def create_service(data: ServiceIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin', 'dispatcher', 'merchant'))):
    if actor.role == "merchant" and (data.quoted_total_dop is not None or data.operator_fee_dop is not None):
        raise HTTPException(status_code=403, detail="Los importes los define el equipo de despacho")
    service = Service(code='DEX-' + uuid4().hex[:12].upper(), company_id=actor.company_id, created_by=actor.id, status='pending', **data.model_dump(mode='json'))
    db.add(service)
    db.flush()
    add_event(db, service, actor, 'created', 'Solicitud registrada; pendiente de asignación')
    publish(db,actor.company_id,'service_created',service.id)
    db.commit()
    return get_accessible(db, actor, service.id)

@router.get('/{service_id}', response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return get_accessible(db, actor, service_id)

@router.post('/{service_id}/quote', response_model=ServiceOut)
def quote_service(service_id: int, data: QuoteIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin', 'dispatcher'))):
    service = get_accessible(db, actor, service_id)
    if service.status != 'pending':
        raise HTTPException(status_code=409, detail='Cotización solo permitida antes de la asignación')
    service.quoted_total_dop = data.quoted_total_dop
    service.operator_fee_dop = data.operator_fee_dop
    add_event(db, service, actor, 'quote_set', 'Cotización confirmada por despacho')
    publish(db,actor.company_id,'quote_updated',service.id)
    db.commit()
    db.expire(service, ["events"])
    return get_accessible(db, actor, service_id)

@router.post('/{service_id}/assign', response_model=ServiceOut)
def assign_service(service_id: int, data: AssignmentIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin','dispatcher'))):
    service = get_accessible(db, actor, service_id)
    # PostgreSQL serializa las asignaciones sobre la fila del operador.
    if service.status != 'pending':
        raise HTTPException(status_code=409, detail='Solo se puede asignar una solicitud pendiente')
    operator = db.scalar(select(Operator).where(Operator.id == data.operator_id).with_for_update())
    if not operator or operator.company_id != actor.company_id or not operator.verified or operator.verification_status != 'approved' or not operator.active or not documents_valid(operator):
        raise HTTPException(status_code=422, detail='Operador no disponible, sin aprobación documental o con documentos vencidos')
    if operator.kind != service.kind:
        raise HTTPException(status_code=422, detail='Operador incompatible con esta modalidad')
    busy = db.scalar(select(Service.id).where(Service.company_id==actor.company_id,Service.operator_id==operator.id,
        Service.status.in_(['assigned','en_route','on_site'])).limit(1))
    if busy:
        raise HTTPException(status_code=409, detail='El operador ya atiende un servicio activo')
    service.operator_id = operator.id
    service.status = 'assigned'
    add_event(db, service, actor, 'assigned', f'Asignación al operador #{operator.id}')
    publish(db,actor.company_id,'service_assigned',service.id)
    db.commit()
    db.expire(service, ["events"])
    return get_accessible(db, actor, service_id)

@router.post('/{service_id}/status', response_model=ServiceOut)
def change_status(service_id: int, data: StatusIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin', 'dispatcher', 'driver'))):
    service = get_accessible(db, actor, service_id)
    if data.status.value not in ALLOWED.get(service.status, set()):
        raise HTTPException(status_code=409, detail=f'Transición inválida: {service.status} → {data.status.value}')
    if actor.role == 'driver':
        if data.status == Status.canceled:
            raise HTTPException(status_code=403, detail='El conductor debe solicitar cancelación a despacho')
        if service.operator_id is None:
            raise HTTPException(status_code=403, detail='La solicitud debe estar asignada')
    if data.status == Status.canceled and (not data.note or len(data.note.strip()) < 4):
        raise HTTPException(status_code=422, detail='Indique el motivo de cancelación')
    if data.status == Status.completed:
        if not data.note or len(data.note.strip()) < 4:
            raise HTTPException(status_code=422, detail='Se requiere constancia de entrega o servicio')
        service.proof_note = data.note.strip()
    service.status = data.status.value
    add_event(db, service, actor, 'status_changed', f'{data.status.value}: {data.note or "Sin observaciones"}')
    publish(db,actor.company_id,'status_changed',service.id)
    db.commit()
    db.expire(service, ["events"])
    return get_accessible(db, actor, service_id)
