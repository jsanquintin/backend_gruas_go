from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.dependencies import get_db
from app.core.security import get_current_user
from app.database.models import Service
from app.crud.service import get_user_services
from app.schemas.service import ServiceResponse, ServiceRequestCreate
from app.crud.service import update_service_status

router = APIRouter()

@router.get("/", response_model=List[ServiceResponse])
def get_services_endpoint(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return services

@router.post("/request", response_model=ServiceResponse)
def create_service_request(service: ServiceRequestCreate, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    new_service = Service(
        client_id=service.client_id,
        pickup_lat=service.pickup_lat,
        pickup_lng=service.pickup_lng,
        destination_lat=service.destination_lat,
        destination_lng=service.destination_lng,
        status=1,
        created_by=current_user["email"]  
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return {"error": "Service not found"}
    return service

@router.put("/services/{service_id}/accept", summary="Aceptar Servicio")
async def accept_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "driver":
        raise HTTPException(status_code=403, detail="Solo conductores pueden aceptar servicios")

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    if service.client_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="No puedes aceptar tu propio servicio")

    try:
        service = update_service_status(db, service_id, "accepted", current_user["id"])
        return {"message": "Servicio aceptado exitosamente", "service": service}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/services/{service_id}/complete", summary="Completar Servicio")
async def complete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "driver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo conductores pueden completar servicios")

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    if service.client_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="No puedes completar tu propio servicio")

    return update_service_status(db, service_id, "completed", current_user["id"])


@router.put("/services/{service_id}/cancel", summary="Cancelar Servicio")
async def cancel_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden cancelar servicios")
    return update_service_status(db, service_id, "cancelled", current_user["id"])

@router.get("/services/user/{user_id}", summary="Listar Servicios por Usuario")
async def list_user_services(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return get_user_services(db, user_id)

