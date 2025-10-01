from pydantic import BaseModel
from typing import Optional

class ServiceRequestCreate(BaseModel):
    client_id: int
    pickup_lat: float
    pickup_lng: float
    destination_lat: float
    destination_lng: float

    class Config:
        orm_mode = True

class ServiceResponse(BaseModel):
    id: int
    client_id: int
    pickup_lat: float
    pickup_lng: float
    destination_lat: float
    destination_lng: float
    status: str

    class Config:
        orm_mode = True


class ServiceOut(BaseModel):
    id: int
    client_id: int
    driver_id: int | None
    status: str

    class Config:
        orm_mode = True

class update_service_status(BaseModel):
    status: str
    notes: Optional[str] = None
