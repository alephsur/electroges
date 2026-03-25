from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class SupplierCreate(BaseModel):
    name: str
    tax_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    contact_person: str | None = None
    payment_terms: str | None = None
    notes: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    contact_person: str | None = None
    payment_terms: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tax_id: str | None
    email: str | None
    phone: str | None
    address: str | None
    contact_person: str | None
    payment_terms: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    skip: int
    limit: int
