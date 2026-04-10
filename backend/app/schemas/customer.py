from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Addresses ─────────────────────────────────────────────────────────────────

class CustomerAddressCreate(BaseModel):
    address_type: Literal["fiscal", "service"] = "service"
    label: str | None = None
    street: str
    city: str
    postal_code: str
    province: str | None = None
    is_default: bool = False


class CustomerAddressUpdate(BaseModel):
    address_type: Literal["fiscal", "service"] | None = None
    label: str | None = None
    street: str | None = None
    city: str | None = None
    postal_code: str | None = None
    province: str | None = None
    is_default: bool | None = None


class CustomerAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    address_type: str
    label: str | None
    street: str
    city: str
    postal_code: str
    province: str | None
    is_default: bool
    created_at: datetime


# ── Documents ─────────────────────────────────────────────────────────────────

class CustomerDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    name: str
    file_path: str
    file_size_bytes: int | None
    document_type: str
    created_at: datetime


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    customer_type: Literal["individual", "company", "community"] = "individual"
    name: str
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    contact_person: str | None = None
    notes: str | None = None
    # Optional initial address
    initial_address: CustomerAddressCreate | None = None


class CustomerUpdate(BaseModel):
    customer_type: Literal["individual", "company", "community"] | None = None
    name: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    contact_person: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class CustomerSummary(BaseModel):
    """Lightweight schema for the list view — no heavy relations."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_type: str
    name: str
    tax_id: str | None
    email: str | None
    phone: str | None
    contact_person: str | None
    is_active: bool
    # Calculated metrics (defaults to 0 until dependent modules exist)
    active_work_orders: int = 0
    total_billed: float = 0.0
    pending_amount: float = 0.0
    last_activity_at: datetime | None = None
    # Primary address (the is_default one or the first)
    primary_address: CustomerAddressResponse | None = None
    created_at: datetime


class CustomerResponse(CustomerSummary):
    """Full schema for the detail view — includes relations."""
    phone_secondary: str | None
    notes: str | None
    addresses: list[CustomerAddressResponse] = []
    documents: list[CustomerDocumentResponse] = []
    updated_at: datetime


class CustomerListResponse(BaseModel):
    items: list[CustomerSummary]
    total: int
    skip: int
    limit: int


# ── Timeline ──────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    """
    Unified timeline event for a customer.
    Aggregates activity from all modules in chronological order.
    Optional fields are filled depending on the event type.
    """
    event_type: Literal[
        "site_visit",
        "budget_created",
        "budget_sent",
        "budget_accepted",
        "budget_rejected",
        "work_order_created",
        "work_order_closed",
        "invoice_issued",
        "invoice_paid",
    ]
    event_date: datetime
    title: str           # Descriptive text for the event
    subtitle: str | None  # Additional detail (reference number, amount, etc.)
    reference_id: UUID   # ID of the related object (for navigation)
    reference_type: str  # "site_visit" | "budget" | "work_order" | "invoice"
    amount: float | None = None  # For monetary events
    status: str | None = None      # Current status of the related object


class CustomerTimeline(BaseModel):
    customer_id: UUID
    events: list[TimelineEvent]
    # Quick metrics calculated when building the timeline
    total_site_visits: int = 0
    total_budgets: int = 0
    total_work_orders: int = 0
    total_invoiced: float = 0.0
    total_pending: float = 0.0
