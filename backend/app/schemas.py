from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Role(str, Enum):
    admin = 'admin'
    dispatcher = 'dispatcher'
    merchant = 'merchant'
    driver = 'driver'

class Kind(str, Enum):
    delivery = 'delivery'
    roadside = 'roadside'

class ServiceType(str, Enum):
    parcel = 'parcel'
    scheduled_route = 'scheduled_route'
    tow = 'tow'
    jumpstart = 'jumpstart'
    tire_change = 'tire_change'
    fuel = 'fuel'
    mechanical = 'mechanical'

class Status(str, Enum):
    pending = 'pending'
    assigned = 'assigned'
    en_route = 'en_route'
    on_site = 'on_site'
    completed = 'completed'
    canceled = 'canceled'

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: Role
    name: str

class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12)
    role: Role

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: Role

class OperatorIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    kind: Kind
    vehicle_type: str = Field(min_length=2, max_length=30)
    license_plate: str | None = Field(default=None, max_length=20)
    user_id: int | None = None
    verified: bool = False

class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    kind: Kind
    vehicle_type: str
    license_plate: str | None
    user_id: int | None
    verified: bool
    active: bool
    verification_status: str
    license_number: str | None
    license_expires_on: date | None
    registration_reference: str | None
    insurance_policy: str | None
    insurance_expires_on: date | None
    verification_note: str | None
    verified_at: datetime | None
    verified_by: int | None

class OperatorDocumentsIn(BaseModel):
    @field_validator('license_number', 'registration_reference', 'insurance_policy', mode='after')
    @classmethod
    def reject_blank_document_references(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError('La referencia documental debe tener al menos 3 caracteres reales')
        return value

    license_number: str = Field(min_length=3, max_length=80)
    license_expires_on: date
    registration_reference: str = Field(min_length=3, max_length=120)
    insurance_policy: str = Field(min_length=3, max_length=120)
    insurance_expires_on: date

class VerificationIn(BaseModel):
    status: str = Field(pattern='^(approved|rejected|suspended|pending)$')
    note: str = Field(min_length=12, max_length=1000)
    documents_checked: bool = False

    @field_validator('note')
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 12:
            raise ValueError('El motivo de decisión debe tener al menos 12 caracteres reales')
        return value

class OperatorReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    action: str
    note: str
    created_at: datetime

class QuoteIn(BaseModel):
    quoted_total_dop: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    operator_fee_dop: Decimal = Field(ge=0, decimal_places=2, max_digits=12)

    @model_validator(mode="after")
    def correct_total(self):
        if self.operator_fee_dop > self.quoted_total_dop:
            raise ValueError("El pago al operador no puede exceder el total")
        return self

class ServiceIn(BaseModel):
    kind: Kind
    service_type: ServiceType
    customer_name: str = Field(min_length=2, max_length=120)
    customer_phone: str = Field(min_length=7, max_length=40)
    pickup_address: str = Field(min_length=5, max_length=500)
    destination_address: str | None = Field(default=None, max_length=500)
    lat: Decimal | None = Field(default=None, ge=-90, le=90)
    lng: Decimal | None = Field(default=None, ge=-180, le=180)
    destination_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    destination_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)
    recipient_name: str | None = Field(default=None, max_length=120)
    recipient_phone: str | None = Field(default=None, max_length=40)
    package_description: str | None = Field(default=None, max_length=500)
    vehicle_plate: str | None = Field(default=None, max_length=20)
    vehicle_description: str | None = Field(default=None, max_length=200)
    quoted_total_dop: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    operator_fee_dop: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)

    @model_validator(mode='after')
    def validate_kind(self):
        if self.kind == Kind.delivery and self.service_type not in (ServiceType.parcel, ServiceType.scheduled_route):
            raise ValueError('Tipo de servicio no corresponde a Delivery')
        if self.kind == Kind.roadside and self.service_type not in (ServiceType.tow, ServiceType.jumpstart, ServiceType.tire_change, ServiceType.fuel, ServiceType.mechanical):
            raise ValueError('Tipo de servicio no corresponde a Asistencia Vial')
        if self.service_type in (ServiceType.parcel, ServiceType.scheduled_route, ServiceType.tow) and not self.destination_address:
            raise ValueError('Se requiere dirección de destino para paquetes, rutas y grúas')
        if self.kind == Kind.delivery and self.service_type == ServiceType.parcel:
            if not self.recipient_name or len(self.recipient_name.strip()) < 2:
                raise ValueError('Indique el nombre del destinatario')
            if not self.recipient_phone or len(self.recipient_phone.strip()) < 7:
                raise ValueError('Indique el teléfono del destinatario')
            if not self.package_description or len(self.package_description.strip()) < 3:
                raise ValueError('Describa el paquete')
        if self.kind == Kind.roadside and (not self.vehicle_plate or len(self.vehicle_plate.strip()) < 3):
            raise ValueError('Indique la placa del vehículo atendido')
        if (self.lat is None) != (self.lng is None):
            raise ValueError('Latitud y longitud deben enviarse juntas')
        if (self.destination_lat is None) != (self.destination_lng is None):
            raise ValueError('Coordenadas del destino deben enviarse juntas')
        if self.quoted_total_dop is not None and self.operator_fee_dop is not None and self.operator_fee_dop > self.quoted_total_dop:
            raise ValueError('Pago al operador no puede superar el precio total')
        return self

class AssignmentIn(BaseModel):
    operator_id: int

class StatusIn(BaseModel):
    status: Status
    note: str | None = Field(default=None, max_length=1000)

class ServiceEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    event_type: str
    detail: str
    created_at: datetime

class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    kind: Kind
    service_type: ServiceType
    status: Status
    operator_id: int | None
    customer_name: str
    customer_phone: str
    pickup_address: str
    destination_address: str | None
    lat: Decimal | None
    lng: Decimal | None
    destination_lat: Decimal | None
    destination_lng: Decimal | None
    quoted_total_dop: Decimal | None
    operator_fee_dop: Decimal | None
    notes: str | None
    proof_note: str | None
    recipient_name: str | None
    recipient_phone: str | None
    package_description: str | None
    vehicle_plate: str | None
    vehicle_description: str | None
    created_at: datetime
    events: list[ServiceEventOut] = []

class DashboardOut(BaseModel):
    total: int
    pending: int
    active: int
    completed: int
    canceled: int
    delivery: int
    roadside: int


class LocationIn(BaseModel):
    lat: Decimal = Field(ge=-90, le=90, decimal_places=7)
    lng: Decimal = Field(ge=-180, le=180, decimal_places=7)
    accuracy_m: float = Field(ge=0, le=5000)

class OperatorPositionOut(BaseModel):
    operator_id: int
    name: str
    kind: Kind
    lat: Decimal
    lng: Decimal
    accuracy_m: float
    recorded_at: datetime
    online: bool
    available: bool

class TariffIn(BaseModel):
    service_type: ServiceType
    base_dop: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    per_km_dop: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    minimum_dop: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    operator_base_dop: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    active: bool = True

class TariffOut(TariffIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: Kind
    updated_at: datetime

class PriceEstimateOut(BaseModel):
    service_type: ServiceType
    mode: str
    distance_km: Decimal | None
    suggested_total_dop: Decimal
    suggested_operator_fee_dop: Decimal
    warning: str
