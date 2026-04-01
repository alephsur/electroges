"""Schemas for the Dashboard module."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class BudgetStats(BaseModel):
    total: int
    draft: int
    sent: int
    accepted: int
    rejected: int
    expired: int
    total_amount: Decimal
    accepted_amount: Decimal
    conversion_rate: float  # percentage 0–100


class WorkOrderStats(BaseModel):
    total: int
    draft: int
    active: int
    pending_closure: int
    closed: int
    cancelled: int
    active_count: int  # draft + active + pending_closure


class InvoiceStats(BaseModel):
    total: int
    draft: int
    sent: int
    paid: int
    cancelled: int
    overdue_count: int
    total_invoiced: Decimal
    total_collected: Decimal
    total_pending: Decimal
    overdue_amount: Decimal
    avg_collection_days: float | None


class PurchaseOrderStats(BaseModel):
    total: int
    pending: int
    received: int
    cancelled: int


class SiteVisitStats(BaseModel):
    total: int
    scheduled: int
    in_progress: int
    completed: int
    cancelled: int
    no_show: int


class MonthlyRevenue(BaseModel):
    month: str   # "2025-01"
    label: str   # "Ene 25"
    invoiced: Decimal
    collected: Decimal


class TopCustomer(BaseModel):
    customer_id: str
    customer_name: str
    invoiced: Decimal
    invoice_count: int


class OverdueInvoiceItem(BaseModel):
    id: str
    invoice_number: str
    customer_name: str
    total: Decimal
    pending_amount: Decimal
    days_overdue: int


class PendingBudgetItem(BaseModel):
    id: str
    budget_number: str
    customer_name: str
    total: Decimal
    days_since_sent: int


class RecentActivityItem(BaseModel):
    id: str
    entity_type: str   # "invoice" | "work_order" | "budget" | "site_visit" | "purchase_order"
    entity_number: str
    customer_name: str | None
    status: str
    date: datetime


class DashboardSummary(BaseModel):
    date_from: date
    date_to: date
    budgets: BudgetStats
    work_orders: WorkOrderStats
    invoices: InvoiceStats
    purchase_orders: PurchaseOrderStats
    site_visits: SiteVisitStats
    monthly_revenue: list[MonthlyRevenue]
    top_customers: list[TopCustomer]
    overdue_invoices: list[OverdueInvoiceItem]
    pending_budgets: list[PendingBudgetItem]
    low_stock_items_count: int
    recent_activity: list[RecentActivityItem]
