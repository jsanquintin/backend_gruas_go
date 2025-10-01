from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear la base declarativa
Base = declarative_base()

# Crear el motor de la base de datos
engine = create_engine(
    settings.DATABASE_URL,
    echo=True  # Opcional: para depuración
)

# Configurar la sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

