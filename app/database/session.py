from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear la base declarativa
Base = declarative_base()

# Crear el motor de la base de datos compatible con psycopg3 y SQLAlchemy 2.0
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False, future=True)

# Configurar la sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

