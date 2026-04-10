from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


# ── Materials ─────────────────────────────────────────────────────────────────

class SiteVisitMaterialCreate(BaseModel):
    inventory_item_id: UUID | None = None
    description: str | None = None
    estimated_qty: Decimal
    unit: str | None = None
    unit_cost: Decimal | None = None

    @model_validator(mode="after")
    def require_description_or_item(self) -> "SiteVisitMaterialCreate":
        if not self.inventory_item_id and not self.description:
            raise ValueError(
                "Debes indicar un material del inventario o una descripción libre"
            )
        return self


class SiteVisitMaterialUpdate(BaseModel):
    description: str | None = None
    estimated_qty: Decimal | None = None
    unit: str | None = None
    unit_cost: Decimal | None = None


class SiteVisitMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_visit_id: UUID
    inventory_item_id: UUID | None
    inventory_item_name: str | None = None
    description: str | None
    estimated_qty: float
    unit: str | None
    unit_cost: float | None
    subtotal: float | None = None
    created_at: datetime


# ── Photos ────────────────────────────────────────────────────────────────────

class SiteVisitPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_visit_id: UUID
    file_path: str
    file_size_bytes: int | None
    caption: str | None
    sort_order: int
    created_at: datetime


class SiteVisitPhotoUpdate(BaseModel):
    caption: str | None = None
    sort_order: int | None = None


# ── Documents ─────────────────────────────────────────────────────────────────

class SiteVisitDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_visit_id: UUID
    name: str
    file_path: str
    file_size_bytes: int | None
    document_type: str
    created_at: datetime


# ── Site Visit ────────────────────────────────────────────────────────────────

class SiteVisitCreate(BaseModel):
    customer_id: UUID | None = None
    customer_address_id: UUID | None = None
    address_text: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    visit_date: datetime
    estimated_duration_hours: Decimal | None = None
    description: str | None = None
    work_scope: str | None = None
    technical_notes: str | None = None
    estimated_hours: Decimal | None = None
    estimated_budget: Decimal | None = None

    @model_validator(mode="after")
    def validate_contact_and_address(self) -> "SiteVisitCreate":
        if not self.customer_id and not self.contact_name:
            raise ValueError(
                "El nombre de contacto es obligatorio cuando no hay cliente registrado"
            )
        if not self.customer_address_id and not self.address_text:
            raise ValueError(
                "Indica una dirección del cliente o escribe la dirección de la visita"
            )
        return self


class SiteVisitUpdate(BaseModel):
    customer_id: UUID | None = None
    customer_address_id: UUID | None = None
    address_text: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    visit_date: datetime | None = None
    estimated_duration_hours: Decimal | None = None
    description: str | None = None
    work_scope: str | None = None
    technical_notes: str | None = None
    estimated_hours: Decimal | None = None
    estimated_budget: Decimal | None = None


class SiteVisitStatusUpdate(BaseModel):
    status: Literal["scheduled", "in_progress", "completed", "cancelled", "no_show"]
    notes: str | None = None


class SiteVisitLinkCustomer(BaseModel):
    customer_id: UUID
    customer_address_id: UUID | None = None


class SiteVisitReorderPhotos(BaseModel):
    photo_ids: list[UUID]


class SiteVisitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID | None
    customer_name: str | None = None
    customer_type: str | None = None
    address_display: str
    contact_name: str | None
    visit_date: datetime
    status: str
    description: str | None
    estimated_budget: float | None
    has_photos: bool = False
    has_documents: bool = False
    materials_count: int = 0
    budgets_count: int = 0
    created_at: datetime


class SiteVisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID | None
    customer_name: str | None = None
    customer_type: str | None = None
    customer_address_id: UUID | None
    address_text: str | None
    address_display: str
    contact_name: str | None
    contact_phone: str | None
    visit_date: datetime
    estimated_duration_hours: float | None
    status: str
    description: str | None
    work_scope: str | None
    technical_notes: str | None
    estimated_hours: float | None
    estimated_budget: float | None
    materials: list[SiteVisitMaterialResponse] = []
    photos: list[SiteVisitPhotoResponse] = []
    documents: list[SiteVisitDocumentResponse] = []
    materials_count: int = 0
    budgets_count: int = 0
    created_at: datetime
    updated_at: datetime


class SiteVisitListResponse(BaseModel):
    items: list[SiteVisitSummary]
    total: int
    skip: int
    limit: int
