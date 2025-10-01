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
    print("USUARIO ENCONTRADO:", user)
    print("CONTRASEÑA RECIBIDA:", password)
    print("HASH GUARDADO:", user.hashed_password if user else "N/A")

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Incluye el ID del usuario en el token
    #access_token = create_access_token(data={"email": user.email, "role": user.role, "id": user.id})
    access_token = create_access_token(data={"email": user.email, "role_id": user.role_id, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    # Verificar si el usuario existe
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generar un token de recuperación válido por 30 minutos
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=30))

    # Simular envío de correo (implementa un sistema de correos en producción)
    print(f"Recovery token for {email}: {token}")

    return {"msg": "Check your email for a recovery link"}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    try:
        # Decodificar el token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Buscar al usuario por correo
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Actualizar la contraseña
    hashed_password = get_password_hash(new_password)
    update_user_password(db, user.id, hashed_password)

    return {"msg": "Password reset successfully"}
