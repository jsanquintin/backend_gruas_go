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

# Función para verificar una contraseña en texto plano contra su hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña ingresada coincide con el hash almacenado.
    """
    return pwd_context.verify(plain_password, hashed_password)


# Función para hashear contraseñas
def get_password_hash(password: str) -> str:
    """
    Genera un hash de la contraseña proporcionada.
    """
    return pwd_context.hash(password)


# Función para crear un token JWT
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Crea un token JWT firmado con un tiempo de expiración opcional.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "sub": data.get("email"),  # Este es el email del usuario
        "role": data.get("role"),  # Este es el rol del usuario
        "id": data.get("id"),      # Este es el ID del usuario
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Función para decodificar y verificar un token JWT
def decode_access_token(token: str) -> dict:
    """
    Decodifica y verifica un token JWT.
    - token: Token JWT a verificar.
    - Retorna el contenido decodificado si es válido.
    - Lanza un error si el token es inválido o ha expirado.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

# Función para obtener el usuario actual desde el token JWT
def get_current_user(token: HTTPAuthorizationCredentials = Security(security)) -> dict:
    try:
        payload = decode_access_token(token.credentials)
        user_id = payload.get("id")
        email = payload.get("sub")
        role = payload.get("role")
        if email is None or user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return {"id": user_id, "email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

