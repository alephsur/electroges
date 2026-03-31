"""Schemas for the WorkOrder module."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Task Materials ────────────────────────────────────────────────────────────

class TaskMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    inventory_item_id: UUID
    inventory_item_name: str
    inventory_item_unit: str
    estimated_quantity: Decimal
    consumed_quantity: Decimal
    pending_quantity: Decimal
    unit_cost: Decimal
    estimated_cost: Decimal
    actual_cost: Decimal


class TaskMaterialCreate(BaseModel):
    inventory_item_id: UUID
    task_id: UUID
    estimated_quantity: Decimal = Field(gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class TaskMaterialConsume(BaseModel):
    consumed_quantity: Decimal = Field(ge=0)
    notes: str | None = None


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    sort_order: int = 0


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    actual_hours: Decimal | None = Field(default=None, ge=0)
    sort_order: int | None = None


class TaskStatusUpdate(BaseModel):
    status: Literal["pending", "in_progress", "completed", "cancelled"]
    actual_hours: Decimal | None = Field(default=None, ge=0)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    origin_budget_line_id: UUID | None
    name: str
    description: str | None
    status: str
    sort_order: int
    unit_price: Decimal | None
    estimated_hours: Decimal | None
    actual_hours: Decimal | None
    materials: list[TaskMaterialResponse] = []
    estimated_cost: Decimal
    actual_cost: Decimal
    is_certified: bool
    certification_id: UUID | None
    created_at: datetime


# ── Linked Purchase Orders ────────────────────────────────────────────────────

class WorkOrderPurchaseOrderLink(BaseModel):
    purchase_order_id: UUID
    notes: str | None = None


class LinkedPOLineResponse(BaseModel):
    """Embedded line inside a LinkedPurchaseOrderResponse."""
    inventory_item_name: str | None
    description: str | None
    quantity: Decimal
    unit_cost: Decimal
    subtotal: Decimal


class LinkedPurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_order_id: UUID
    supplier_id: UUID
    order_number: str
    supplier_name: str
    supplier_email: str | None
    supplier_phone: str | None
    status: str
    order_date: str
    expected_date: str | None
    total_amount: Decimal
    notes: str | None
    lines: list[LinkedPOLineResponse] = []


# ── Certifications ────────────────────────────────────────────────────────────

class CertificationItemCreate(BaseModel):
    task_id: UUID
    amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class CertificationCreate(BaseModel):
    items: list[CertificationItemCreate]
    notes: str | None = None


class CertificationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    task_name: str
    task_status: str
    amount: Decimal
    notes: str | None


class CertificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    certification_number: str
    status: str
    notes: str | None
    invoice_id: UUID | None
    items: list[CertificationItemResponse] = []
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


# ── Work Order ────────────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    customer_id: UUID
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class WorkOrderUpdate(BaseModel):
    address: str | None = None
    notes: str | None = None


class WorkOrderStatusUpdate(BaseModel):
    status: Literal["active", "closed", "cancelled"]
    notes: str | None = None


class WorkOrderKPIs(BaseModel):
    total_tasks: int
    completed_tasks: int
    progress_pct: Decimal

    estimated_hours: Decimal
    actual_hours: Decimal
    hours_deviation_pct: Decimal

    budget_cost: Decimal
    actual_cost: Decimal
    cost_deviation_pct: Decimal

    total_task_materials: int
    fully_consumed_materials: int
    pending_materials: int

    budget_total: Decimal
    total_certified: Decimal
    total_invoiced: Decimal
    pending_to_certify: Decimal
    margin_real_pct: Decimal

    total_purchase_orders: int
    pending_purchase_orders: int


class WorkOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_number: str
    customer_id: UUID
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    origin_budget_id: UUID | None
    budget_number: str | None
    status: str
    address: str | None
    total_tasks: int
    completed_tasks: int
    progress_pct: Decimal
    budget_total: Decimal
    total_certified: Decimal
    actual_cost: Decimal
    created_at: datetime


class WorkOrderResponse(WorkOrderSummary):
    other_lines_notes: str | None
    notes: str | None
    assigned_to: UUID | None
    tasks: list[TaskResponse] = []
    certifications: list[CertificationResponse] = []
    purchase_order_links: list[LinkedPurchaseOrderResponse] = []
    delivery_notes: list["DeliveryNoteResponse"] = []
    kpis: WorkOrderKPIs
    updated_at: datetime


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderSummary]
    total: int
    skip: int
    limit: int


# ── Delivery Notes ────────────────────────────────────────────────────────────

class DeliveryNoteItemCreate(BaseModel):
    line_type: Literal["material", "labor", "other"] = "material"
    description: str = Field(..., max_length=500)
    inventory_item_id: UUID | None = None
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="ud", max_length=20)
    unit_price: Decimal = Field(ge=0)
    sort_order: int = 0


class DeliveryNoteCreate(BaseModel):
    delivery_date: date
    requested_by: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    items: list[DeliveryNoteItemCreate] = []


class DeliveryNoteUpdate(BaseModel):
    delivery_date: date | None = None
    requested_by: str | None = None
    notes: str | None = None
    items: list[DeliveryNoteItemCreate] | None = None


class DeliveryNoteItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    delivery_note_id: UUID
    line_type: str
    description: str
    inventory_item_id: UUID | None
    inventory_item_name: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal
    sort_order: int


class DeliveryNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    delivery_note_number: str
    status: str
    delivery_date: str
    requested_by: str | None
    notes: str | None
    items: list[DeliveryNoteItemResponse] = []
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


# ── New Purchase Order for Work Order ─────────────────────────────────────────

class NewPurchaseOrderForWorkOrder(BaseModel):
    supplier_id: UUID
    order_date: date
    expected_date: date | None = None
    notes: str | None = None
    lines: list[dict] = []  # Delegated to PurchaseOrderLineCreate validation


# ── Document send actions ─────────────────────────────────────────────────────

class SendDocumentEmail(BaseModel):
    to_email: EmailStr
    subject: str | None = None
    message: str | None = None


class WhatsAppLinkResponse(BaseModel):
    url: str
    phone: str


# Resolve forward references
WorkOrderResponse.model_rebuild()
