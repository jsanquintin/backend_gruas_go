import base64
import hashlib
import hmac
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.settings import get_settings

bearer = HTTPBearer(auto_error=False)
ITERATIONS = 600_000

def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError('La contraseña debe tener al menos 12 caracteres')
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf8'), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}'

def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, count, salt, expected = encoded.split('$')
        if algo != 'pbkdf2_sha256': return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf8'), base64.b64decode(salt), int(count))
        return hmac.compare_digest(candidate, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False

def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user.id), 'iat': now, 'exp': now + timedelta(minutes=settings.jwt_expires_minutes), 'iss': 'degaritao-express'}, settings.jwt_secret, algorithm='HS256')

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if creds is None or creds.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Autenticación requerida')
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=['HS256'], issuer='degaritao-express')
        user_id = int(payload['sub'])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail='Token inválido o vencido')
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='Usuario inactivo o inexistente')
    return user

def require_roles(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail='No tiene permiso para esta operación')
        return user
    return guard
