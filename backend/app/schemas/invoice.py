from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: date
    method: Literal["transfer", "cash", "card", "direct_debit"]
    reference: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    amount: float
    payment_date: date
    method: str
    reference: str | None
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Lines ─────────────────────────────────────────────────────────────────────

class InvoiceLineCreate(BaseModel):
    origin_type: Literal["certification", "task", "manual"] = "manual"
    origin_id: UUID | None = None
    description: str
    quantity: Decimal = Field(gt=0)
    unit: str | None = None
    unit_price: Decimal = Field(ge=0)
    line_discount_pct: Decimal = Field(ge=0, le=100, default=Decimal("0.00"))
    sort_order: int = 0


class InvoiceLineUpdate(BaseModel):
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    line_discount_pct: Decimal | None = None
    sort_order: int | None = None


class InvoiceLineResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    origin_type: str
    origin_id: UUID | None
    sort_order: int
    description: str
    quantity: float
    unit: str | None
    unit_price: float
    line_discount_pct: float
    subtotal: float
    model_config = {"from_attributes": True}


# ── Totals ────────────────────────────────────────────────────────────────────

class InvoiceTotals(BaseModel):
    subtotal_before_discount: float
    discount_amount: float
    taxable_base: float
    tax_amount: float
    total: float
    total_paid: float
    pending_amount: float
    is_fully_paid: bool


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    customer_id: UUID
    work_order_id: UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal = Field(ge=0, le=100, default=Decimal("0.00"))
    notes: str | None = None
    client_notes: str | None = None
    lines: list[InvoiceLineCreate] = []


class InvoiceFromWorkOrderRequest(BaseModel):
    work_order_id: UUID
    certification_ids: list[UUID] = []
    task_ids: list[UUID] = []
    extra_lines: list[InvoiceLineCreate] = []
    issue_date: date | None = None
    due_date: date | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal = Decimal("0.00")
    notes: str | None = None
    client_notes: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_source(self) -> "InvoiceFromWorkOrderRequest":
        if not self.certification_ids and not self.task_ids and not self.extra_lines:
            raise ValueError(
                "Añade al menos una certificación, tarea o línea manual a la factura"
            )
        return self


class InvoiceUpdate(BaseModel):
    issue_date: date | None = None
    due_date: date | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal | None = None
    notes: str | None = None
    client_notes: str | None = None


class RectificationRequest(BaseModel):
    reason: str = Field(min_length=5)
    notes: str | None = None


class InvoiceSummary(BaseModel):
    id: UUID
    invoice_number: str
    is_rectification: bool
    rectifies_invoice_id: UUID | None
    customer_id: UUID
    customer_name: str
    work_order_id: UUID | None
    work_order_number: str | None
    status: str
    effective_status: str
    issue_date: date
    due_date: date
    total: float
    total_paid: float
    pending_amount: float
    days_overdue: int
    has_pdf: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class InvoiceResponse(InvoiceSummary):
    discount_pct: float
    tax_rate: float
    notes: str | None
    client_notes: str | None
    lines: list[InvoiceLineResponse] = []
    payments: list[PaymentResponse] = []
    totals: InvoiceTotals
    updated_at: datetime


class InvoiceFilters(BaseModel):
    q: str | None = None
    customer_id: UUID | None = None
    work_order_id: UUID | None = None
    status: str | None = None
    overdue_only: bool = False
    date_from: date | None = None
    date_to: date | None = None
    skip: int = 0
    limit: int = 50


class InvoiceListResponse(BaseModel):
    items: list[InvoiceSummary]
    total: int


class ReorderLinesRequest(BaseModel):
    line_ids: list[UUID]


class PaymentReminderResponse(BaseModel):
    invoice_number: str
    customer_name: str
    pending_amount: float
    days_overdue: int
    reminder_text: str
