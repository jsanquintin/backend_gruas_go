import os
os.environ['JWT_SECRET'] = 'only_for_pytest_' + 'X' * 60
os.environ['DATABASE_URL'] = 'sqlite://'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.models import Company, User
from app.security import hash_password

@pytest.fixture
def env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    local = sessionmaker(bind=engine, expire_on_commit=False)
    with local() as db:
        c1=Company(name='DEGARITAO Express')
        c2=Company(name='Otra empresa')
        db.add_all([c1,c2]);db.flush()
        actors={}
        for name,email,role,company in [('Admin','admin@example.com','admin',c1),('Despacho','dispatch@example.com','dispatcher',c1),('Comercio','merchant@example.com','merchant',c1),('Conductor','driver@example.com','driver',c1),('Externo','outside@example.com','admin',c2)]:
            u=User(name=name,email=email,role=role,company_id=company.id,password_hash=hash_password('Valida-2026-123'))
            db.add(u);db.flush();actors[role if role!='admin' else ('admin' if company==c1 else 'outside')]=u
        db.commit()
    def override():
        with local() as db:
            yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as client:
        tokens={}
        for role,email in [('admin','admin@example.com'),('dispatcher','dispatch@example.com'),('merchant','merchant@example.com'),('driver','driver@example.com'),('outside','outside@example.com')]:
            r=client.post('/api/v1/auth/login',json={'email':email,'password':'Valida-2026-123'})
            assert r.status_code==200, r.text
            tokens[role]= {'Authorization':'Bearer '+r.json()['access_token']}
        yield client,tokens,local
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
