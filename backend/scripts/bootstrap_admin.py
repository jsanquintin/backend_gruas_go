"""Crear solamente el administrador inicial si aún no existe.

No imprime credenciales ni cambia contraseñas existentes. Retirar ADMIN_PASSWORD
una vez comprobado el alta en el panel de Railway.
"""
import os
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Company, User
from app.security import hash_password

email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
password = os.environ.get('ADMIN_PASSWORD', '')
if not email or not password:
    raise SystemExit('ADMIN_EMAIL y ADMIN_PASSWORD son requeridos para el alta inicial')
if len(password) < 12:
    raise SystemExit('ADMIN_PASSWORD necesita mínimo 12 caracteres')

with SessionLocal() as db:
    if db.scalar(select(User.id).where(User.email == email)):
        print('Administrador inicial ya registrado; no se modifica')
    else:
        company = db.scalar(select(Company).where(Company.name == 'DEGARITAO Express'))
        if not company:
            company = Company(name='DEGARITAO Express')
            db.add(company)
            db.flush()
        db.add(User(company_id=company.id, name='Administrador Express', email=email,
                    role='admin', password_hash=hash_password(password)))
        db.commit()
        print('Administrador inicial creado')
