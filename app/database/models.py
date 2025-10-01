from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database.session import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServiceStatus(Base):
    __tablename__ = "service_status"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role")

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    destination_lat = Column(Float)
    destination_lng = Column(Float)

    status_id = Column(Integer, ForeignKey("service_status.id"), nullable=False)
    status = relationship("ServiceStatus")

    client = relationship("User", foreign_keys=[client_id])
    driver = relationship("User", foreign_keys=[driver_id])

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
