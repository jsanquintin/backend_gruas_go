from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut
from app.security import create_token, current_user, verify_password

router = APIRouter(prefix='/auth', tags=['Autenticación'])

@router.post('/login', response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Credenciales inválidas')
    return TokenOut(access_token=create_token(user), role=user.role, name=user.name)

@router.get('/me', response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
