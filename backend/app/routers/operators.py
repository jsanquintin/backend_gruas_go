from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Operator, OperatorReview, User
from app.events import publish
from app.schemas import OperatorDocumentsIn, OperatorIn, OperatorOut, OperatorReviewOut, VerificationIn
from app.security import require_roles

router = APIRouter(prefix='/operators', tags=['Operadores'])


def get_operator(db: Session, actor: User, operator_id: int) -> Operator:
    op = db.get(Operator, operator_id)
    if not op or op.company_id != actor.company_id:
        raise HTTPException(status_code=404, detail='Operador no encontrado')
    return op


def documents_valid(op: Operator) -> bool:
    today = datetime.now(timezone.utc).date()
    return bool(all(isinstance(value, str) and len(value.strip()) >= 3 for value in (
                op.license_plate, op.license_number, op.registration_reference, op.insurance_policy))
                and op.license_expires_on and op.insurance_expires_on
                and op.license_expires_on >= today and op.insurance_expires_on >= today)


def audit(db: Session, op: Operator, actor: User, action: str, note: str):
    db.add(OperatorReview(operator_id=op.id, actor_id=actor.id, action=action, note=note))


@router.get('', response_model=list[OperatorOut])
def list_operators(db: Session = Depends(get_db), actor: User = Depends(require_roles('admin', 'dispatcher'))):
    return db.scalars(select(Operator).where(Operator.company_id == actor.company_id).order_by(Operator.id)).all()


@router.post('', response_model=OperatorOut, status_code=201)
def create_operator(data: OperatorIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin'))):
    if data.user_id:
        target = db.get(User, data.user_id)
        if not target or target.company_id != actor.company_id or target.role != 'driver':
            raise HTTPException(status_code=422, detail='Operador debe asociarse con conductor válido de la empresa')
        if db.scalar(select(Operator.id).where(Operator.user_id == data.user_id)):
            raise HTTPException(status_code=409, detail='Conductor ya está vinculado a otro operador')
    safe = data.model_dump(mode='json')
    safe['verified'] = False
    operator = Operator(company_id=actor.company_id, verification_status='pending', **safe)
    db.add(operator)
    db.flush()
    audit(db, operator, actor, 'created', 'Operador registrado, pendiente de documentación y aprobación')
    publish(db,actor.company_id,'operator_created',operator.id)
    db.commit()
    db.refresh(operator)
    return operator


@router.patch('/{operator_id}/documents', response_model=OperatorOut)
def save_documents(operator_id: int, data: OperatorDocumentsIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin'))):
    op = get_operator(db, actor, operator_id)
    for key, val in data.model_dump().items():
        setattr(op, key, val)
    # Cualquier cambio de documentos revoca una autorización previa.
    op.verified = False
    op.verification_status = 'pending'
    op.verified_by = None
    op.verified_at = None
    op.verification_note = 'Documentos actualizados, pendiente de nueva revisión'
    audit(db, op, actor, 'documents_updated', 'Referencias y fechas documentales actualizadas; aprobación revocada')
    publish(db,actor.company_id,'operator_documents_changed',op.id)
    db.commit()
    db.refresh(op)
    return op


@router.patch('/{operator_id}/verification', response_model=OperatorOut)
def verify(operator_id: int, data: VerificationIn, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin'))):
    op = get_operator(db, actor, operator_id)
    if data.status == 'approved':
        if not data.documents_checked:
            raise HTTPException(status_code=422, detail='Debe confirmar la revisión presencial o comprobable de los documentos antes de aprobar.')
        if not documents_valid(op):
            raise HTTPException(status_code=422, detail='Faltan licencia, placa, matrícula, póliza o hay documentos vencidos. Guarde y valide los datos primero.')
    op.verification_status = data.status
    op.verified = data.status == 'approved'
    op.verification_note = data.note.strip()
    op.verified_by = actor.id
    op.verified_at = datetime.now(timezone.utc)
    audit(db, op, actor, data.status, ('Revisión manual confirmada. ' if data.status == 'approved' else '') + data.note.strip())
    publish(db,actor.company_id,'operator_verified',op.id)
    db.commit()
    db.refresh(op)
    return op


@router.get('/{operator_id}/reviews', response_model=list[OperatorReviewOut])
def list_reviews(operator_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles('admin', 'dispatcher'))):
    get_operator(db, actor, operator_id)
    return db.scalars(select(OperatorReview).where(OperatorReview.operator_id == operator_id).order_by(OperatorReview.id.desc())).all()
