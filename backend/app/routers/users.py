from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import UserIn, UserOut
from app.security import hash_password, require_roles

router = APIRouter(prefix='/users', tags=['Usuarios'])

@router.get('', response_model=list[UserOut])
def users(db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    return db.scalars(select(User).where(User.company_id == admin.company_id).order_by(User.id)).all()

@router.post('', response_model=UserOut, status_code=201)
def create_user(data: UserIn, db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    email = data.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail='Correo ya registrado')
    user = User(company_id=admin.company_id, name=data.name, email=email, role=data.role.value, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
