from sqlalchemy.orm import Session
from app.database.models import Service

def get_services(db: Session):
    return db.query(Service).all()

def update_service_status(db: Session, service_id: int, status: str, driver_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise ValueError("Servicio no encontrado")

    if status == "accepted" and service.status != "pending":
        raise ValueError("El servicio ya fue aceptado")

    service.driver_id = driver_id if status == "accepted" else service.driver_id
    service.status = status
    db.commit()
    db.refresh(service)
    return service

def get_user_services(db: Session, user_id: int):
    return db.query(Service).filter(
        (Service.client_id == user_id) | (Service.driver_id == user_id)
    ).all()
