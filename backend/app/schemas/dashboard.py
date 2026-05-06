"""Schemas for the Dashboard module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class BudgetStats(BaseModel):
    total: int
    draft: int
    sent: int
    accepted: int
    rejected: int
    expired: int
    total_amount: float
    accepted_amount: float
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
    total_invoiced: float
    total_collected: float
    total_pending: float
    overdue_amount: float
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
    invoiced: float
    collected: float


class TopCustomer(BaseModel):
    customer_id: str
    customer_name: str
    invoiced: float
    invoice_count: int


class OverdueInvoiceItem(BaseModel):
    id: str
    invoice_number: str
    customer_name: str
    total: float
    pending_amount: float
    days_overdue: int


class PendingBudgetItem(BaseModel):
    id: str
    budget_number: str
    customer_name: str
    total: float
    days_since_sent: int


class RecentActivityItem(BaseModel):
    id: str
    entity_type: str   # "invoice" | "work_order" | "budget" | "site_visit" | "purchase_order"
    entity_number: str
    customer_name: str | None
    status: str
    date: datetime


class RecentActivityPage(BaseModel):
    items: list[RecentActivityItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class WorkOrderProfitabilityItem(BaseModel):
    work_order_id: str
    work_order_number: str
    customer_name: str
    budgeted_hours: float
    actual_hours: float
    budgeted_material_cost: float
    actual_material_cost: float
    budgeted_revenue: float
    total_certified: float        # sum of certification items (issued + invoiced)
    revenue_base: float           # total_certified if > 0, else budgeted_revenue
    margin_pct: float | None


class CashFlowBucket(BaseModel):
    bucket: str   # "0_30" | "31_60" | "61_90" | "91_plus"
    label: str    # "0–30 días", "31–60 días", …
    amount: float
    invoice_count: int


class TopDebtorCustomer(BaseModel):
    customer_id: str
    customer_name: str
    total_overdue: float
    invoice_count: int
    avg_days_overdue: float


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
    work_order_profitability: list[WorkOrderProfitabilityItem]
    cash_flow_buckets: list[CashFlowBucket]
    top_debtors: list[TopDebtorCustomer]
