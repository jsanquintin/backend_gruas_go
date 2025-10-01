import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database.session import Base, engine
from app.database.models import User, Service, Role, ServiceStatus

def init_db():
    Base.metadata.create_all(bind=engine)

