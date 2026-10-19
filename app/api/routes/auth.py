from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.dependencies import get_db  # Importa correctamente get_db
from app.database.session import SessionLocal
from app.schemas.user import UserCreate
from app.crud.user import create_user, get_user_by_email, update_user_password
from app.core.security import verify_password, get_password_hash, create_access_token
from datetime import timedelta
from app.core.config import settings
from jose import jwt, JWTError

router = APIRouter()

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    user_in_db = get_user_by_email(db, user.email)
    if user_in_db:
        return {"error": "Email already registered"}
    #user.password = get_password_hash(user.password)
    new_user = create_user(db, user)
    return {"id": new_user.id, "email": new_user.email}

@router.post("/login", summary="Login de usuario")
async def login_user(email: str, password: str, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)




    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Incluye el ID del usuario en el token
    #access_token = create_access_token(data={"email": user.email, "role": user.role, "id": user.id})
    access_token = create_access_token(data={"email": user.email, "role": user.role.name, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


# Seguridad: estos endpoints se desactivan hasta implementar un canal verificado
# de recuperación y tokens de un solo uso. El legado imprimía los tokens en logs.
@router.post("/forgot-password", status_code=503)
def forgot_password(email: str):
    raise HTTPException(status_code=503, detail="Recuperación temporalmente deshabilitada")

@router.post("/reset-password", status_code=503)
def reset_password(token: str, new_password: str):
    raise HTTPException(status_code=503, detail="Recuperación temporalmente deshabilitada")
