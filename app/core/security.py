from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import logging

# Configuración del contexto para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Middleware para obtener el token
security = HTTPBearer()

logger = logging.getLogger(__name__)

def log_failed_login_attempt(email: str):
    logger.warning(f"Intento de inicio de sesión fallido para el usuario: {email}")

# --------------------------------------------------------------------
# 🔐 Función para verificar una contraseña
# --------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña ingresada coincide con el hash almacenado.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verificando contraseña: {e}")
        raise HTTPException(status_code=500, detail="Error al verificar contraseña.")


# --------------------------------------------------------------------
# 🔐 Función para hashear contraseñas
# --------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    """
    Genera un hash de la contraseña proporcionada.
    - Corta la contraseña a 72 bytes máximo (límite de bcrypt).
    """
    # Evitar error de longitud por bcrypt (>72 bytes)
    password = password.encode("utf-8")[:72].decode("utf-8", "ignore")

    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error generando hash: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el hash de la contraseña.")


# --------------------------------------------------------------------
# 🧾 Función para crear un token JWT
# --------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Crea un token JWT firmado con un tiempo de expiración opcional.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "sub": str(data.get("email")),   # Siempre convertir a str
        "role": str(data.get("role")),   # Siempre convertir a str
        "id": int(data.get("id")),       # Asegurar tipo entero
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# --------------------------------------------------------------------
# 🔍 Función para decodificar/verificar un token JWT
# --------------------------------------------------------------------
def decode_access_token(token: str) -> dict:
    """
    Decodifica y verifica un token JWT.
    Lanza un error si el token es inválido o ha expirado.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")


# --------------------------------------------------------------------
# 👤 Obtener el usuario actual desde el token JWT
# --------------------------------------------------------------------
def get_current_user(token: HTTPAuthorizationCredentials = Security(security)) -> dict:
    try:
        payload = decode_access_token(token.credentials)
        user_id = payload.get("id")
        email = payload.get("sub")
        role = payload.get("role")

        if not all([email, user_id, role]):
            raise HTTPException(status_code=401, detail="Token inválido o incompleto.")

        return {"id": user_id, "email": email, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")
