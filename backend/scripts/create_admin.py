"""Ejecutar: ADMIN_EMAIL=... ADMIN_PASSWORD=... python -m scripts.create_admin"""
import os
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Company, User
from app.security import hash_password

email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
password = os.environ.get('ADMIN_PASSWORD', '')
name = os.environ.get('ADMIN_NAME', 'Administrador Express')
if not email or not password:
    raise SystemExit('Defina ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 12 caracteres)')
with SessionLocal() as db:
    company = db.scalar(select(Company).where(Company.name == 'DEGARITAO Express'))
    if not company:
        company = Company(name='DEGARITAO Express')
        db.add(company)
        db.flush()
    if db.scalar(select(User).where(User.email == email)):
        raise SystemExit('El administrador ya existe; no se cambió la contraseña')
    db.add(User(company_id=company.id, name=name, email=email, role='admin', password_hash=hash_password(password)))
    db.commit()
print('Administrador creado correctamente')
