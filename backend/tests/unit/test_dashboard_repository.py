"""
Unit tests for DashboardRepository computation methods and DashboardService.

Strategy:
  - All `_compute_*` / `_build_*` / helper functions are pure Python — tested
    by calling them directly on a repo instance with a dummy session.
  - `get_summary` and data loaders are async; session.execute is AsyncMock so
    each scalars().all() call is given an explicit list via side_effect.
  - DashboardService is thin (delegates to repo); tested separately at the bottom.

No real database needed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.budget import BudgetStatus
from app.models.invoice import InvoiceStatus
from app.models.site_visit import SiteVisitStatus
from app.models.work_order import WorkOrderStatus
from app.repositories.dashboard import (
    DashboardRepository,
    _budget_total,
    _invoice_collected,
    _invoice_total,
)
from app.schemas.dashboard import DashboardSummary

TENANT_ID = uuid.uuid4()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return date.today()


def _repo() -> DashboardRepository:
    """Return a repo with a mock session — used for calling pure methods."""
    return DashboardRepository(session=AsyncMock(), tenant_id=TENANT_ID)


# ── Factories ──────────────────────────────────────────────────────────────────

def make_budget_line(**kwargs) -> MagicMock:
    ln = MagicMock()
    ln.quantity = Decimal("2")
    ln.unit_price = Decimal("100.00")
    ln.line_discount_pct = Decimal("0")
    for k, v in kwargs.items():
        setattr(ln, k, v)
    return ln


def make_budget(**kwargs) -> MagicMock:
    b = MagicMock()
    b.id = uuid.uuid4()
    b.tenant_id = TENANT_ID
    b.budget_number = "PRES-2025-0001"
    b.status = BudgetStatus.DRAFT
    b.issue_date = date(2025, 6, 1)
    b.valid_until = date(2025, 7, 1)
    b.discount_pct = Decimal("0")
    b.tax_rate = Decimal("21")
    b.lines = [make_budget_line()]
    b.customer = MagicMock()
    b.customer.name = "Cliente Test"
    b.customer_id = uuid.uuid4()
    b.is_latest_version = True
    b.created_at = _now()
    b.updated_at = _now()
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def make_payment(**kwargs) -> MagicMock:
    p = MagicMock()
    p.amount = Decimal("100.00")
    p.payment_date = date(2025, 6, 10)
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


def make_invoice(**kwargs) -> MagicMock:
    inv = MagicMock()
    inv.id = uuid.uuid4()
    inv.tenant_id = TENANT_ID
    inv.invoice_number = "FAC-2025-0001"
    inv.status = InvoiceStatus.DRAFT
    inv.issue_date = date(2025, 6, 1)
    inv.due_date = date(2025, 7, 1)
    inv.discount_pct = Decimal("0")
    inv.tax_rate = Decimal("21")
    inv.lines = [make_budget_line()]  # same structure: quantity, unit_price, line_discount_pct
    inv.payments = []
    inv.customer = MagicMock()
    inv.customer.name = "Cliente SA"
    inv.customer_id = uuid.uuid4()
    inv.is_rectification = False
    inv.created_at = _now()
    inv.updated_at = _now()
    for k, v in kwargs.items():
        setattr(inv, k, v)
    return inv


def make_work_order(**kwargs) -> MagicMock:
    wo = MagicMock()
    wo.id = uuid.uuid4()
    wo.tenant_id = TENANT_ID
    wo.work_order_number = "OBR-2025-0001"
    wo.status = WorkOrderStatus.DRAFT
    wo.customer = MagicMock()
    wo.customer.name = "Cliente WO"
    wo.customer_id = uuid.uuid4()
    wo.created_at = _now()
    wo.updated_at = _now()
    for k, v in kwargs.items():
        setattr(wo, k, v)
    return wo


def make_purchase_order(**kwargs) -> MagicMock:
    po = MagicMock()
    po.id = uuid.uuid4()
    po.tenant_id = TENANT_ID
    po.order_number = "PED-2025-0001"
    po.status = "pending"
    po.order_date = date(2025, 6, 1)
    po.supplier = MagicMock()
    po.supplier.name = "Proveedor SA"
    po.created_at = _now()
    po.updated_at = _now()
    for k, v in kwargs.items():
        setattr(po, k, v)
    return po


def make_site_visit(**kwargs) -> MagicMock:
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.tenant_id = TENANT_ID
    sv.status = SiteVisitStatus.SCHEDULED
    sv.customer = MagicMock()
    sv.customer.name = "Cliente SV"
    sv.created_at = _now()
    sv.updated_at = _now()
    for k, v in kwargs.items():
        setattr(sv, k, v)
    return sv


def _scalars_result(items: list) -> MagicMock:
    """Build the MagicMock that session.execute() returns: result.scalars().all() == items."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _scalar_result(value) -> MagicMock:
    """Build the MagicMock that session.execute() returns: result.scalar() == value."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


# ── _budget_total helper ───────────────────────────────────────────────────────

class TestBudgetTotalHelper:
    def test_single_line_no_discounts(self):
        b = make_budget(
            lines=[make_budget_line(quantity=Decimal("2"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("21"),
        )
        # subtotal=200, taxable=200, total=200*1.21=242
        assert _budget_total(b) == Decimal("242.00")

    def test_line_discount_applied(self):
        b = make_budget(
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("10"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        # 100 * (1 - 0.10) = 90
        assert _budget_total(b) == Decimal("90.0")

    def test_global_discount_applied(self):
        b = make_budget(
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            discount_pct=Decimal("20"),
            tax_rate=Decimal("0"),
        )
        # subtotal=100, taxable=100*(1-0.20)=80
        assert _budget_total(b) == Decimal("80.0")

    def test_multiple_lines(self):
        b = make_budget(
            lines=[
                make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                 line_discount_pct=Decimal("0")),
                make_budget_line(quantity=Decimal("2"), unit_price=Decimal("50"),
                                 line_discount_pct=Decimal("0")),
            ],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert _budget_total(b) == Decimal("200")

    def test_empty_lines(self):
        b = make_budget(lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("21"))
        assert _budget_total(b) == Decimal("0")


# ── _invoice_total helper ──────────────────────────────────────────────────────

class TestInvoiceTotalHelper:
    def test_basic_calculation(self):
        inv = make_invoice(
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("200"),
                                    line_discount_pct=Decimal("0"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("21"),
        )
        assert _invoice_total(inv) == Decimal("242.0")

    def test_combined_discounts_and_tax(self):
        inv = make_invoice(
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("1000"),
                                    line_discount_pct=Decimal("10"))],
            discount_pct=Decimal("5"),
            tax_rate=Decimal("21"),
        )
        # line: 1000 * 0.90 = 900
        # global: 900 * 0.95 = 855
        # tax:    855 * 1.21 = 1034.55
        assert _invoice_total(inv) == Decimal("1034.55")


# ── _invoice_collected helper ──────────────────────────────────────────────────

class TestInvoiceCollectedHelper:
    def test_no_payments(self):
        inv = make_invoice(payments=[])
        assert _invoice_collected(inv) == Decimal("0")

    def test_single_payment(self):
        inv = make_invoice(payments=[make_payment(amount=Decimal("500"))])
        assert _invoice_collected(inv) == Decimal("500")

    def test_multiple_payments(self):
        inv = make_invoice(payments=[
            make_payment(amount=Decimal("300")),
            make_payment(amount=Decimal("200")),
        ])
        assert _invoice_collected(inv) == Decimal("500")


# ── _compute_budget_stats ──────────────────────────────────────────────────────

class TestComputeBudgetStats:
    def test_empty_list(self):
        repo = _repo()
        stats = repo._compute_budget_stats([], _today())
        assert stats.total == 0
        assert stats.conversion_rate == 0.0
        assert stats.total_amount == Decimal("0.00")

    def test_counts_all_statuses(self):
        today = date(2025, 6, 15)
        budgets = [
            make_budget(status=BudgetStatus.DRAFT, valid_until=date(2025, 7, 1)),
            make_budget(status=BudgetStatus.SENT, valid_until=date(2025, 7, 1)),
            make_budget(status=BudgetStatus.ACCEPTED, valid_until=date(2025, 7, 1)),
            make_budget(status=BudgetStatus.REJECTED, valid_until=date(2025, 7, 1)),
        ]
        repo = _repo()
        stats = repo._compute_budget_stats(budgets, today)
        assert stats.total == 4
        assert stats.draft == 1
        assert stats.sent == 1
        assert stats.accepted == 1
        assert stats.rejected == 1

    def test_sent_past_valid_until_becomes_expired(self):
        today = date(2025, 6, 15)
        # valid_until is in the past → reclassified as expired
        b = make_budget(
            status=BudgetStatus.SENT,
            valid_until=date(2025, 6, 10),  # already past
            lines=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_budget_stats([b], today)
        assert stats.expired == 1
        assert stats.sent == 0

    def test_conversion_rate_calculation(self):
        today = date(2025, 6, 15)
        budgets = [
            make_budget(status=BudgetStatus.ACCEPTED, valid_until=date(2025, 7, 1),
                        lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0")),
            make_budget(status=BudgetStatus.ACCEPTED, valid_until=date(2025, 7, 1),
                        lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0")),
            make_budget(status=BudgetStatus.REJECTED, valid_until=date(2025, 7, 1),
                        lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0")),
        ]
        repo = _repo()
        stats = repo._compute_budget_stats(budgets, today)
        # 2 accepted / (2+1) decided * 100 = 66.7
        assert stats.conversion_rate == pytest.approx(66.7, abs=0.1)

    def test_conversion_rate_zero_when_no_decided(self):
        today = date(2025, 6, 15)
        b = make_budget(status=BudgetStatus.DRAFT, valid_until=date(2025, 7, 1),
                        lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        repo = _repo()
        stats = repo._compute_budget_stats([b], today)
        assert stats.conversion_rate == 0.0

    def test_accepted_amount_sums_accepted_only(self):
        today = date(2025, 6, 15)
        line = make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                line_discount_pct=Decimal("0"))
        accepted = make_budget(status=BudgetStatus.ACCEPTED, valid_until=date(2025, 7, 1),
                               lines=[line], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        draft = make_budget(status=BudgetStatus.DRAFT, valid_until=date(2025, 7, 1),
                            lines=[line], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        repo = _repo()
        stats = repo._compute_budget_stats([accepted, draft], today)
        assert stats.accepted_amount == Decimal("100.00")
        assert stats.total_amount == Decimal("200.00")

    def test_total_amount_quantized(self):
        today = date(2025, 6, 15)
        line = make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                line_discount_pct=Decimal("0"))
        b = make_budget(status=BudgetStatus.DRAFT, valid_until=date(2025, 7, 1),
                        lines=[line], discount_pct=Decimal("0"), tax_rate=Decimal("21"))
        repo = _repo()
        stats = repo._compute_budget_stats([b], today)
        # 121.00 — two decimal places
        assert stats.total_amount == Decimal("121.00")


# ── _compute_work_order_stats ──────────────────────────────────────────────────

class TestComputeWorkOrderStats:
    def test_empty_list(self):
        repo = _repo()
        stats = repo._compute_work_order_stats([])
        assert stats.total == 0
        assert stats.active_count == 0

    def test_all_statuses(self):
        wos = [
            make_work_order(status=WorkOrderStatus.DRAFT),
            make_work_order(status=WorkOrderStatus.ACTIVE),
            make_work_order(status=WorkOrderStatus.ACTIVE),
            make_work_order(status=WorkOrderStatus.PENDING_CLOSURE),
            make_work_order(status=WorkOrderStatus.CLOSED),
            make_work_order(status=WorkOrderStatus.CANCELLED),
        ]
        repo = _repo()
        stats = repo._compute_work_order_stats(wos)
        assert stats.total == 6
        assert stats.draft == 1
        assert stats.active == 2
        assert stats.pending_closure == 1
        assert stats.closed == 1
        assert stats.cancelled == 1

    def test_active_count_aggregates_draft_active_pending(self):
        wos = [
            make_work_order(status=WorkOrderStatus.DRAFT),
            make_work_order(status=WorkOrderStatus.ACTIVE),
            make_work_order(status=WorkOrderStatus.PENDING_CLOSURE),
            make_work_order(status=WorkOrderStatus.CLOSED),
        ]
        repo = _repo()
        stats = repo._compute_work_order_stats(wos)
        # draft(1) + active(1) + pending_closure(1)
        assert stats.active_count == 3

    def test_all_closed(self):
        wos = [make_work_order(status=WorkOrderStatus.CLOSED) for _ in range(3)]
        repo = _repo()
        stats = repo._compute_work_order_stats(wos)
        assert stats.active_count == 0
        assert stats.closed == 3


# ── _compute_invoice_stats ─────────────────────────────────────────────────────

class TestComputeInvoiceStats:
    def test_empty_list(self):
        repo = _repo()
        stats = repo._compute_invoice_stats([], _today())
        assert stats.total == 0
        assert stats.avg_collection_days is None

    def test_paid_invoice_counted(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.PAID,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 7, 1),
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[make_payment(amount=Decimal("121"), payment_date=date(2025, 6, 11))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("21"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        assert stats.paid == 1
        assert stats.total_collected == Decimal("121.00")

    def test_overdue_invoice_when_sent_and_past_due_date(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 5, 1),
            due_date=date(2025, 6, 10),  # past today
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        assert stats.overdue_count == 1
        assert stats.overdue_amount == Decimal("100.00")
        assert stats.sent == 0  # not counted as sent when overdue

    def test_sent_invoice_not_overdue(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 7, 1),  # future
            lines=[],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        assert stats.sent == 1
        assert stats.overdue_count == 0

    def test_draft_and_cancelled_counted(self):
        today = date(2025, 6, 15)
        invoices = [
            make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[],
                         discount_pct=Decimal("0"), tax_rate=Decimal("0")),
            make_invoice(status=InvoiceStatus.CANCELLED, lines=[], payments=[],
                         discount_pct=Decimal("0"), tax_rate=Decimal("0")),
        ]
        repo = _repo()
        stats = repo._compute_invoice_stats(invoices, today)
        assert stats.draft == 1
        assert stats.cancelled == 1

    def test_avg_collection_days_computed(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.PAID,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 7, 1),
            lines=[],
            payments=[make_payment(amount=Decimal("0"), payment_date=date(2025, 6, 11))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        # payment_date(June 11) - issue_date(June 1) = 10 days
        assert stats.avg_collection_days == 10.0

    def test_avg_collection_days_none_when_no_paid(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 7, 1),
            lines=[],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        assert stats.avg_collection_days is None

    def test_total_pending_calculation(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 7, 1),
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[make_payment(amount=Decimal("40"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        stats = repo._compute_invoice_stats([inv], today)
        # total_invoiced=100, collected=40, pending=60
        assert stats.total_pending == Decimal("60.00")


# ── _compute_purchase_order_stats ─────────────────────────────────────────────

class TestComputePurchaseOrderStats:
    def test_empty(self):
        repo = _repo()
        stats = repo._compute_purchase_order_stats([])
        assert stats.total == 0

    def test_all_statuses(self):
        pos = [
            make_purchase_order(status="pending"),
            make_purchase_order(status="pending"),
            make_purchase_order(status="received"),
            make_purchase_order(status="cancelled"),
        ]
        repo = _repo()
        stats = repo._compute_purchase_order_stats(pos)
        assert stats.total == 4
        assert stats.pending == 2
        assert stats.received == 1
        assert stats.cancelled == 1


# ── _compute_site_visit_stats ──────────────────────────────────────────────────

class TestComputeSiteVisitStats:
    def test_empty(self):
        repo = _repo()
        stats = repo._compute_site_visit_stats([])
        assert stats.total == 0
        assert stats.no_show == 0

    def test_all_statuses(self):
        svs = [
            make_site_visit(status=SiteVisitStatus.SCHEDULED),
            make_site_visit(status=SiteVisitStatus.IN_PROGRESS),
            make_site_visit(status=SiteVisitStatus.COMPLETED),
            make_site_visit(status=SiteVisitStatus.COMPLETED),
            make_site_visit(status=SiteVisitStatus.CANCELLED),
            make_site_visit(status=SiteVisitStatus.NO_SHOW),
        ]
        repo = _repo()
        stats = repo._compute_site_visit_stats(svs)
        assert stats.total == 6
        assert stats.scheduled == 1
        assert stats.in_progress == 1
        assert stats.completed == 2
        assert stats.cancelled == 1
        assert stats.no_show == 1


# ── _compute_monthly_revenue ───────────────────────────────────────────────────

class TestComputeMonthlyRevenue:
    def test_single_month_empty(self):
        repo = _repo()
        result = repo._compute_monthly_revenue([], date(2025, 6, 1), date(2025, 6, 30))
        assert len(result) == 1
        assert result[0].month == "2025-06"
        assert result[0].invoiced == Decimal("0.00")

    def test_month_label_format(self):
        repo = _repo()
        result = repo._compute_monthly_revenue([], date(2025, 1, 1), date(2025, 1, 31))
        assert result[0].label == "Ene 25"

    def test_december_label(self):
        repo = _repo()
        result = repo._compute_monthly_revenue([], date(2025, 12, 1), date(2025, 12, 31))
        assert result[0].label == "Dic 25"

    def test_multi_month_range_creates_all_months(self):
        repo = _repo()
        result = repo._compute_monthly_revenue([], date(2025, 1, 1), date(2025, 3, 31))
        assert len(result) == 3
        months = [r.month for r in result]
        assert months == ["2025-01", "2025-02", "2025-03"]

    def test_year_boundary_december_to_january(self):
        repo = _repo()
        result = repo._compute_monthly_revenue([], date(2025, 12, 1), date(2026, 1, 31))
        assert len(result) == 2
        assert result[0].month == "2025-12"
        assert result[1].month == "2026-01"

    def test_invoice_amounts_aggregated_by_month(self):
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 6, 15),
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[make_payment(amount=Decimal("50"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        result = repo._compute_monthly_revenue([inv], date(2025, 6, 1), date(2025, 6, 30))
        assert result[0].invoiced == Decimal("100.00")
        assert result[0].collected == Decimal("50.00")

    def test_cancelled_invoices_excluded(self):
        inv = make_invoice(
            status=InvoiceStatus.CANCELLED,
            issue_date=date(2025, 6, 15),
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        result = repo._compute_monthly_revenue([inv], date(2025, 6, 1), date(2025, 6, 30))
        assert result[0].invoiced == Decimal("0.00")

    def test_invoice_outside_range_not_included(self):
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            issue_date=date(2025, 5, 15),  # outside June range
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("1000"),
                                    line_discount_pct=Decimal("0"))],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        repo = _repo()
        result = repo._compute_monthly_revenue([inv], date(2025, 6, 1), date(2025, 6, 30))
        assert result[0].invoiced == Decimal("0.00")


# ── _compute_top_customers ─────────────────────────────────────────────────────

class TestComputeTopCustomers:
    def test_empty_invoices(self):
        repo = _repo()
        result = repo._compute_top_customers([])
        assert result == []

    def test_single_customer(self):
        cid = uuid.uuid4()
        inv = make_invoice(
            status=InvoiceStatus.PAID,
            customer_id=cid,
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("500"),
                                    line_discount_pct=Decimal("0"))],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        inv.customer.name = "Empresa ABC"
        repo = _repo()
        result = repo._compute_top_customers([inv])
        assert len(result) == 1
        assert result[0].customer_name == "Empresa ABC"
        assert result[0].invoiced == Decimal("500.00")
        assert result[0].invoice_count == 1

    def test_aggregates_multiple_invoices_same_customer(self):
        cid = uuid.uuid4()
        line = make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                line_discount_pct=Decimal("0"))
        customer_mock = MagicMock()
        customer_mock.name = "Empresa ABC"

        inv1 = make_invoice(status=InvoiceStatus.PAID, customer_id=cid,
                            lines=[line], payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        inv1.customer = customer_mock
        inv2 = make_invoice(status=InvoiceStatus.PAID, customer_id=cid,
                            lines=[line], payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        inv2.customer = customer_mock
        repo = _repo()
        result = repo._compute_top_customers([inv1, inv2])
        assert len(result) == 1
        assert result[0].invoice_count == 2
        assert result[0].invoiced == Decimal("200.00")

    def test_sorted_by_invoiced_desc(self):
        cid1, cid2 = uuid.uuid4(), uuid.uuid4()
        c1 = MagicMock(); c1.name = "Small"
        c2 = MagicMock(); c2.name = "Big"
        small = make_invoice(status=InvoiceStatus.SENT, customer_id=cid1,
                             lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                                     line_discount_pct=Decimal("0"))],
                             payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        small.customer = c1
        big = make_invoice(status=InvoiceStatus.SENT, customer_id=cid2,
                           lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("500"),
                                                   line_discount_pct=Decimal("0"))],
                           payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        big.customer = c2
        repo = _repo()
        result = repo._compute_top_customers([small, big])
        assert result[0].customer_name == "Big"
        assert result[1].customer_name == "Small"

    def test_max_five_customers(self):
        invoices = []
        for i in range(7):
            cid = uuid.uuid4()
            c = MagicMock(); c.name = f"Customer {i}"
            inv = make_invoice(
                status=InvoiceStatus.PAID, customer_id=cid,
                lines=[make_budget_line(quantity=Decimal("1"),
                                        unit_price=Decimal(str(100 + i)),
                                        line_discount_pct=Decimal("0"))],
                payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"),
            )
            inv.customer = c
            invoices.append(inv)
        repo = _repo()
        result = repo._compute_top_customers(invoices)
        assert len(result) <= 5

    def test_cancelled_excluded(self):
        cid = uuid.uuid4()
        inv = make_invoice(status=InvoiceStatus.CANCELLED, customer_id=cid,
                           lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("999"),
                                                   line_discount_pct=Decimal("0"))],
                           payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        repo = _repo()
        result = repo._compute_top_customers([inv])
        assert result == []


# ── _build_overdue_items ───────────────────────────────────────────────────────

class TestBuildOverdueItems:
    def test_empty(self):
        repo = _repo()
        assert repo._build_overdue_items([], _today()) == []

    def test_days_overdue_calculated(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            due_date=date(2025, 6, 5),  # 10 days ago
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        inv.customer.name = "Cliente Test"
        repo = _repo()
        result = repo._build_overdue_items([inv], today)
        assert result[0].days_overdue == 10

    def test_pending_amount_is_total_minus_collected(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            due_date=date(2025, 6, 5),
            lines=[make_budget_line(quantity=Decimal("1"), unit_price=Decimal("100"),
                                    line_discount_pct=Decimal("0"))],
            payments=[make_payment(amount=Decimal("30"))],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        inv.customer.name = "Test"
        repo = _repo()
        result = repo._build_overdue_items([inv], today)
        assert result[0].pending_amount == Decimal("70.00")

    def test_sorted_by_days_overdue_desc(self):
        today = date(2025, 6, 15)
        inv1 = make_invoice(due_date=date(2025, 6, 10), lines=[],
                            payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        inv1.customer.name = "Reciente"
        inv2 = make_invoice(due_date=date(2025, 5, 1), lines=[],
                            payments=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        inv2.customer.name = "Antiguo"
        repo = _repo()
        result = repo._build_overdue_items([inv1, inv2], today)
        assert result[0].customer_name == "Antiguo"  # more overdue first

    def test_invoice_number_in_result(self):
        today = date(2025, 6, 15)
        inv = make_invoice(
            invoice_number="FAC-2025-0099",
            due_date=date(2025, 6, 1),
            lines=[],
            payments=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        inv.customer.name = "Test"
        repo = _repo()
        result = repo._build_overdue_items([inv], today)
        assert result[0].invoice_number == "FAC-2025-0099"


# ── _build_pending_items ───────────────────────────────────────────────────────

class TestBuildPendingItems:
    def test_empty(self):
        repo = _repo()
        assert repo._build_pending_items([], _today()) == []

    def test_days_since_sent_calculated(self):
        today = date(2025, 6, 15)
        b = make_budget(
            budget_number="PRES-2025-0001",
            issue_date=date(2025, 6, 8),  # 7 days ago
            lines=[],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        b.customer.name = "Constructora"
        repo = _repo()
        result = repo._build_pending_items([b], today)
        assert result[0].days_since_sent == 7

    def test_sorted_by_days_since_sent_desc(self):
        today = date(2025, 6, 15)
        new_b = make_budget(issue_date=date(2025, 6, 12),
                            lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        new_b.customer.name = "Nuevo"
        new_b.budget_number = "PRES-2025-0002"

        old_b = make_budget(issue_date=date(2025, 6, 1),
                            lines=[], discount_pct=Decimal("0"), tax_rate=Decimal("0"))
        old_b.customer.name = "Antiguo"
        old_b.budget_number = "PRES-2025-0001"

        repo = _repo()
        result = repo._build_pending_items([new_b, old_b], today)
        assert result[0].customer_name == "Antiguo"  # more days first

    def test_total_in_result(self):
        today = date(2025, 6, 15)
        line = make_budget_line(quantity=Decimal("1"), unit_price=Decimal("1000"),
                                line_discount_pct=Decimal("0"))
        b = make_budget(
            issue_date=date(2025, 6, 1),
            lines=[line],
            discount_pct=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        b.customer.name = "Test"
        repo = _repo()
        result = repo._build_pending_items([b], today)
        assert result[0].total == Decimal("1000.00")


# ── get_summary (async integration, mocked session) ───────────────────────────

class TestGetSummary:
    async def test_returns_dashboard_summary_with_empty_data(self):
        session = AsyncMock()
        # get_summary calls session.execute multiple times (budgets, work_orders, invoices,
        # purchase_orders, site_visits, overdue_invoices, pending_budgets,
        # low_stock_count, and 5 times in recent_activity)
        empty_scalars = _scalars_result([])
        empty_scalar = _scalar_result(0)

        # We need enough side_effects:
        # _load_budgets, _load_work_orders, _load_invoices, _load_purchase_orders,
        # _load_site_visits, _load_all_overdue_invoices, _load_all_pending_budgets,
        # _count_low_stock_items (scalar), _load_recent_activity (5 calls)
        session.execute.side_effect = [
            empty_scalars,   # budgets
            empty_scalars,   # work_orders
            empty_scalars,   # invoices
            empty_scalars,   # purchase_orders
            empty_scalars,   # site_visits
            empty_scalars,   # overdue invoices
            empty_scalars,   # pending budgets
            empty_scalar,    # low stock count
            empty_scalars,   # recent: invoices
            empty_scalars,   # recent: work_orders
            empty_scalars,   # recent: budgets
            empty_scalars,   # recent: site_visits
            empty_scalars,   # recent: purchase_orders
        ]

        repo = DashboardRepository(session=session, tenant_id=TENANT_ID)
        date_from = date(2025, 6, 1)
        date_to = date(2025, 6, 30)
        summary = await repo.get_summary(date_from, date_to)

        assert isinstance(summary, DashboardSummary)
        assert summary.date_from == date_from
        assert summary.date_to == date_to
        assert summary.budgets.total == 0
        assert summary.work_orders.total == 0
        assert summary.invoices.total == 0
        assert summary.low_stock_items_count == 0
        assert summary.recent_activity == []
        assert len(summary.monthly_revenue) == 1  # one month in range

    async def test_low_stock_count_propagated(self):
        session = AsyncMock()
        empty_scalars = _scalars_result([])

        session.execute.side_effect = [
            empty_scalars, empty_scalars, empty_scalars, empty_scalars,
            empty_scalars, empty_scalars, empty_scalars,
            _scalar_result(7),   # low stock count = 7
            empty_scalars, empty_scalars, empty_scalars, empty_scalars, empty_scalars,
        ]

        repo = DashboardRepository(session=session, tenant_id=TENANT_ID)
        summary = await repo.get_summary(date(2025, 6, 1), date(2025, 6, 30))
        assert summary.low_stock_items_count == 7

    async def test_recent_activity_merged_and_sorted(self):
        session = AsyncMock()
        empty_scalars = _scalars_result([])

        inv = make_invoice()
        inv.invoice_number = "FAC-001"
        inv.status = InvoiceStatus.PAID
        inv.created_at = datetime(2025, 6, 10, 12, 0, tzinfo=timezone.utc)
        inv.customer.name = "Test"

        wo = make_work_order()
        wo.work_order_number = "OBR-001"
        wo.status = WorkOrderStatus.ACTIVE
        wo.created_at = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)  # newer
        wo.customer.name = "Test"

        session.execute.side_effect = [
            empty_scalars, empty_scalars, empty_scalars, empty_scalars,
            empty_scalars, empty_scalars, empty_scalars,
            _scalar_result(0),
            _scalars_result([inv]),    # recent invoices
            _scalars_result([wo]),     # recent work_orders
            empty_scalars,             # recent budgets
            empty_scalars,             # recent site_visits
            empty_scalars,             # recent purchase_orders
        ]

        repo = DashboardRepository(session=session, tenant_id=TENANT_ID)
        summary = await repo.get_summary(date(2025, 6, 1), date(2025, 6, 30))

        assert len(summary.recent_activity) == 2
        # work_order is newer → appears first
        assert summary.recent_activity[0].entity_type == "work_order"
        assert summary.recent_activity[1].entity_type == "invoice"


# ── DashboardService ───────────────────────────────────────────────────────────

class TestDashboardService:
    async def test_delegates_to_repo(self):
        from app.services.dashboard import DashboardService

        mock_summary = MagicMock(spec=DashboardSummary)
        mock_repo = AsyncMock()
        mock_repo.get_summary.return_value = mock_summary

        with patch("app.services.dashboard.DashboardRepository", return_value=mock_repo):
            service = DashboardService(session=AsyncMock(), tenant_id=TENANT_ID)
            date_from = date(2025, 6, 1)
            date_to = date(2025, 6, 30)
            result = await service.get_summary(date_from, date_to)

        mock_repo.get_summary.assert_called_once_with(date_from, date_to)
        assert result is mock_summary

    async def test_passes_tenant_id_to_repo(self):
        from app.services.dashboard import DashboardService

        tenant = uuid.uuid4()
        captured_args = {}

        def capture_repo(session, tenant_id):
            captured_args["tenant_id"] = tenant_id
            m = AsyncMock()
            m.get_summary.return_value = MagicMock()
            return m

        with patch("app.services.dashboard.DashboardRepository", side_effect=capture_repo):
            service = DashboardService(session=AsyncMock(), tenant_id=tenant)
            await service.get_summary(date(2025, 6, 1), date(2025, 6, 30))

        assert captured_args["tenant_id"] == tenant
