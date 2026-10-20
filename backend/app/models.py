from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def now_utc():
    return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = 'companies'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20))  # admin, dispatcher, merchant, driver
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Operator(Base):
    __tablename__ = 'operators'
    __table_args__ = (UniqueConstraint('company_id', 'user_id', name='uq_operator_user'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(20))  # delivery or roadside
    vehicle_type: Mapped[str] = mapped_column(String(30))
    license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')
    license_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    license_expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance_policy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance_expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class OperatorReview(Base):
    __tablename__ = 'operator_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey('operators.id'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Service(Base):
    __tablename__ = 'services'
    __table_args__ = (
        CheckConstraint('quoted_total_dop IS NULL OR quoted_total_dop >= 0', name='nonnegative_price'),
        CheckConstraint('operator_fee_dop IS NULL OR operator_fee_dop >= 0', name='nonnegative_operator_fee'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    operator_id: Mapped[int | None] = mapped_column(ForeignKey('operators.id'), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    service_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(25), default='pending', index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(40))
    pickup_address: Mapped[str] = mapped_column(String(500))
    destination_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    package_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quoted_total_dop: Mapped[Decimal | None] = mapped_column(Numeric(12,2), nullable=True)
    operator_fee_dop: Mapped[Decimal | None] = mapped_column(Numeric(12,2), nullable=True)
    proof_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    destination_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    destination_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    events: Mapped[list['ServiceEvent']] = relationship(back_populates='service', cascade='all, delete-orphan', order_by='ServiceEvent.id')

class ServiceEvent(Base):
    __tablename__ = 'service_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    event_type: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    service: Mapped[Service] = relationship(back_populates='events')


class OperatorLocation(Base):
    __tablename__ = 'operator_locations'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey('operators.id'), index=True)
    lat: Mapped[Decimal] = mapped_column(Numeric(10,7))
    lng: Mapped[Decimal] = mapped_column(Numeric(10,7))
    accuracy_m: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

class Tariff(Base):
    __tablename__ = 'tariffs'
    __table_args__ = (UniqueConstraint('company_id','service_type',name='uq_tariff_company_service'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    service_type: Mapped[str] = mapped_column(String(40))
    base_dop: Mapped[Decimal] = mapped_column(Numeric(12,2))
    per_km_dop: Mapped[Decimal] = mapped_column(Numeric(12,2))
    minimum_dop: Mapped[Decimal] = mapped_column(Numeric(12,2))
    operator_base_dop: Mapped[Decimal] = mapped_column(Numeric(12,2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

class DispatchEvent(Base):
    __tablename__ = 'dispatch_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
