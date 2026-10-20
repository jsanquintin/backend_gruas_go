from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Service, User
from app.schemas import DashboardOut
from app.security import require_roles

router = APIRouter(prefix='/dashboard', tags=['Dashboard'])

@router.get('', response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), actor: User = Depends(require_roles('admin','dispatcher'))):
    base = select(Service.kind, Service.status, func.count(Service.id)).where(Service.company_id == actor.company_id).group_by(Service.kind, Service.status)
    rows = db.execute(base).all()
    total = sum(row[2] for row in rows)
    count = lambda field, value: sum(row[2] for row in rows if row[field] == value)
    return DashboardOut(total=total, pending=count(1,'pending'), active=sum(n for _,status,n in rows if status in ('assigned','en_route','on_site')), completed=count(1,'completed'), canceled=count(1,'canceled'), delivery=count(0,'delivery'), roadside=count(0,'roadside'))
