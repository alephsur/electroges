"""
Unit tests for Dashboard Pydantic schemas.

Pure Python — no database, no mocks, no async.
Covers all schema models: BudgetStats, WorkOrderStats, InvoiceStats,
PurchaseOrderStats, SiteVisitStats, MonthlyRevenue, TopCustomer,
OverdueInvoiceItem, PendingBudgetItem, RecentActivityItem, DashboardSummary.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.dashboard import (
    BudgetStats,
    DashboardSummary,
    InvoiceStats,
    MonthlyRevenue,
    OverdueInvoiceItem,
    PendingBudgetItem,
    PurchaseOrderStats,
    RecentActivityItem,
    SiteVisitStats,
    TopCustomer,
    WorkOrderStats,
)

_NOW = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
_TODAY = date(2025, 6, 15)


# ── BudgetStats ────────────────────────────────────────────────────────────────

class TestBudgetStats:
    def _make(self, **kwargs) -> dict:
        defaults = dict(
            total=10, draft=2, sent=3, accepted=3, rejected=1, expired=1,
            total_amount=Decimal("5000.00"),
            accepted_amount=Decimal("2000.00"),
            conversion_rate=75.0,
        )
        defaults.update(kwargs)
        return defaults

    def test_valid(self):
        s = BudgetStats(**self._make())
        assert s.total == 10
        assert s.conversion_rate == 75.0

    def test_zero_values(self):
        s = BudgetStats(**self._make(total=0, draft=0, sent=0, accepted=0,
                                     rejected=0, expired=0,
                                     total_amount=Decimal("0"),
                                     accepted_amount=Decimal("0"),
                                     conversion_rate=0.0))
        assert s.total == 0
        assert s.conversion_rate == 0.0

    def test_total_field_required(self):
        data = self._make()
        del data["total"]
        with pytest.raises(ValidationError):
            BudgetStats(**data)

    def test_conversion_rate_is_float(self):
        s = BudgetStats(**self._make(conversion_rate=33.3))
        assert isinstance(s.conversion_rate, float)

    def test_amounts_are_decimal(self):
        s = BudgetStats(**self._make())
        assert isinstance(s.total_amount, Decimal)
        assert isinstance(s.accepted_amount, Decimal)


# ── WorkOrderStats ─────────────────────────────────────────────────────────────

class TestWorkOrderStats:
    def _make(self, **kwargs) -> dict:
        defaults = dict(
            total=5, draft=1, active=2, pending_closure=1,
            closed=1, cancelled=0, active_count=4,
        )
        defaults.update(kwargs)
        return defaults

    def test_valid(self):
        s = WorkOrderStats(**self._make())
        assert s.total == 5
        assert s.active_count == 4

    def test_all_zero(self):
        s = WorkOrderStats(**self._make(total=0, draft=0, active=0,
                                        pending_closure=0, closed=0,
                                        cancelled=0, active_count=0))
        assert s.active_count == 0

    def test_active_count_field_required(self):
        data = self._make()
        del data["active_count"]
        with pytest.raises(ValidationError):
            WorkOrderStats(**data)


# ── InvoiceStats ───────────────────────────────────────────────────────────────

class TestInvoiceStats:
    def _make(self, **kwargs) -> dict:
        defaults = dict(
            total=8, draft=1, sent=2, paid=3, cancelled=1,
            overdue_count=1,
            total_invoiced=Decimal("10000.00"),
            total_collected=Decimal("7500.00"),
            total_pending=Decimal("2500.00"),
            overdue_amount=Decimal("500.00"),
            avg_collection_days=15.5,
        )
        defaults.update(kwargs)
        return defaults

    def test_valid(self):
        s = InvoiceStats(**self._make())
        assert s.total == 8
        assert s.avg_collection_days == 15.5

    def test_avg_collection_days_nullable(self):
        s = InvoiceStats(**self._make(avg_collection_days=None))
        assert s.avg_collection_days is None

    def test_amounts_are_decimal(self):
        s = InvoiceStats(**self._make())
        assert isinstance(s.total_invoiced, Decimal)
        assert isinstance(s.overdue_amount, Decimal)

    def test_total_pending_field_required(self):
        data = self._make()
        del data["total_pending"]
        with pytest.raises(ValidationError):
            InvoiceStats(**data)


# ── PurchaseOrderStats ─────────────────────────────────────────────────────────

class TestPurchaseOrderStats:
    def test_valid(self):
        s = PurchaseOrderStats(total=3, pending=1, received=1, cancelled=1)
        assert s.total == 3

    def test_all_zero(self):
        s = PurchaseOrderStats(total=0, pending=0, received=0, cancelled=0)
        assert s.pending == 0

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            PurchaseOrderStats(total=1, pending=1, received=1)


# ── SiteVisitStats ─────────────────────────────────────────────────────────────

class TestSiteVisitStats:
    def test_valid(self):
        s = SiteVisitStats(
            total=6, scheduled=2, in_progress=1,
            completed=2, cancelled=1, no_show=0,
        )
        assert s.no_show == 0
        assert s.total == 6

    def test_all_statuses(self):
        s = SiteVisitStats(
            total=5, scheduled=1, in_progress=1,
            completed=1, cancelled=1, no_show=1,
        )
        assert s.scheduled + s.in_progress + s.completed + s.cancelled + s.no_show == 5

    def test_missing_no_show(self):
        with pytest.raises(ValidationError):
            SiteVisitStats(total=1, scheduled=1, in_progress=0,
                           completed=0, cancelled=0)


# ── MonthlyRevenue ─────────────────────────────────────────────────────────────

class TestMonthlyRevenue:
    def test_valid(self):
        r = MonthlyRevenue(
            month="2025-01",
            label="Ene 25",
            invoiced=Decimal("3000.00"),
            collected=Decimal("2500.00"),
        )
        assert r.month == "2025-01"
        assert r.label == "Ene 25"

    def test_zero_amounts(self):
        r = MonthlyRevenue(
            month="2025-12",
            label="Dic 25",
            invoiced=Decimal("0"),
            collected=Decimal("0"),
        )
        assert r.invoiced == Decimal("0")

    def test_amounts_are_decimal(self):
        r = MonthlyRevenue(month="2025-06", label="Jun 25",
                           invoiced=Decimal("100"), collected=Decimal("50"))
        assert isinstance(r.invoiced, Decimal)
        assert isinstance(r.collected, Decimal)

    def test_fields_required(self):
        with pytest.raises(ValidationError):
            MonthlyRevenue(month="2025-06", label="Jun 25", invoiced=Decimal("0"))


# ── TopCustomer ────────────────────────────────────────────────────────────────

class TestTopCustomer:
    def test_valid(self):
        cid = str(uuid.uuid4())
        t = TopCustomer(
            customer_id=cid,
            customer_name="Empresa ABC",
            invoiced=Decimal("15000.00"),
            invoice_count=5,
        )
        assert t.customer_id == cid
        assert t.invoice_count == 5

    def test_amounts_are_decimal(self):
        t = TopCustomer(
            customer_id=str(uuid.uuid4()),
            customer_name="Test",
            invoiced=Decimal("1000"),
            invoice_count=1,
        )
        assert isinstance(t.invoiced, Decimal)

    def test_missing_customer_name(self):
        with pytest.raises(ValidationError):
            TopCustomer(customer_id=str(uuid.uuid4()),
                        invoiced=Decimal("1000"), invoice_count=1)


# ── OverdueInvoiceItem ─────────────────────────────────────────────────────────

class TestOverdueInvoiceItem:
    def test_valid(self):
        item = OverdueInvoiceItem(
            id=str(uuid.uuid4()),
            invoice_number="FAC-2025-0001",
            customer_name="Cliente SA",
            total=Decimal("1210.00"),
            pending_amount=Decimal("605.00"),
            days_overdue=30,
        )
        assert item.days_overdue == 30
        assert item.invoice_number == "FAC-2025-0001"

    def test_amounts_are_decimal(self):
        item = OverdueInvoiceItem(
            id=str(uuid.uuid4()),
            invoice_number="FAC-2025-0001",
            customer_name="Test",
            total=Decimal("1000"),
            pending_amount=Decimal("500"),
            days_overdue=10,
        )
        assert isinstance(item.total, Decimal)
        assert isinstance(item.pending_amount, Decimal)

    def test_missing_days_overdue(self):
        with pytest.raises(ValidationError):
            OverdueInvoiceItem(
                id=str(uuid.uuid4()),
                invoice_number="FAC-2025-0001",
                customer_name="Test",
                total=Decimal("1000"),
                pending_amount=Decimal("500"),
            )


# ── PendingBudgetItem ──────────────────────────────────────────────────────────

class TestPendingBudgetItem:
    def test_valid(self):
        item = PendingBudgetItem(
            id=str(uuid.uuid4()),
            budget_number="PRES-2025-0001",
            customer_name="Constructora XY",
            total=Decimal("4840.00"),
            days_since_sent=7,
        )
        assert item.days_since_sent == 7
        assert item.budget_number == "PRES-2025-0001"

    def test_amount_is_decimal(self):
        item = PendingBudgetItem(
            id=str(uuid.uuid4()),
            budget_number="PRES-2025-0001",
            customer_name="Test",
            total=Decimal("1000"),
            days_since_sent=3,
        )
        assert isinstance(item.total, Decimal)

    def test_missing_budget_number(self):
        with pytest.raises(ValidationError):
            PendingBudgetItem(
                id=str(uuid.uuid4()),
                customer_name="Test",
                total=Decimal("1000"),
                days_since_sent=3,
            )


# ── RecentActivityItem ─────────────────────────────────────────────────────────

class TestRecentActivityItem:
    def test_valid(self):
        item = RecentActivityItem(
            id=str(uuid.uuid4()),
            entity_type="invoice",
            entity_number="FAC-2025-0001",
            customer_name="Cliente SA",
            status="paid",
            date=_NOW,
        )
        assert item.entity_type == "invoice"
        assert item.status == "paid"

    def test_customer_name_nullable(self):
        item = RecentActivityItem(
            id=str(uuid.uuid4()),
            entity_type="purchase_order",
            entity_number="PED-2025-0001",
            customer_name=None,
            status="pending",
            date=_NOW,
        )
        assert item.customer_name is None

    @pytest.mark.parametrize("entity_type", [
        "invoice", "work_order", "budget", "site_visit", "purchase_order"
    ])
    def test_entity_types(self, entity_type):
        item = RecentActivityItem(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_number="XXX-001",
            customer_name=None,
            status="draft",
            date=_NOW,
        )
        assert item.entity_type == entity_type

    def test_missing_date(self):
        with pytest.raises(ValidationError):
            RecentActivityItem(
                id=str(uuid.uuid4()),
                entity_type="invoice",
                entity_number="FAC-001",
                customer_name=None,
                status="draft",
            )


# ── DashboardSummary ───────────────────────────────────────────────────────────

def _make_budget_stats(**kwargs) -> BudgetStats:
    return BudgetStats(
        total=0, draft=0, sent=0, accepted=0, rejected=0, expired=0,
        total_amount=Decimal("0"), accepted_amount=Decimal("0"),
        conversion_rate=0.0, **kwargs
    )

def _make_work_order_stats(**kwargs) -> WorkOrderStats:
    return WorkOrderStats(
        total=0, draft=0, active=0, pending_closure=0,
        closed=0, cancelled=0, active_count=0, **kwargs
    )

def _make_invoice_stats(**kwargs) -> InvoiceStats:
    return InvoiceStats(
        total=0, draft=0, sent=0, paid=0, cancelled=0, overdue_count=0,
        total_invoiced=Decimal("0"), total_collected=Decimal("0"),
        total_pending=Decimal("0"), overdue_amount=Decimal("0"),
        avg_collection_days=None, **kwargs
    )

def _make_po_stats(**kwargs) -> PurchaseOrderStats:
    return PurchaseOrderStats(total=0, pending=0, received=0, cancelled=0, **kwargs)

def _make_sv_stats(**kwargs) -> SiteVisitStats:
    return SiteVisitStats(
        total=0, scheduled=0, in_progress=0,
        completed=0, cancelled=0, no_show=0, **kwargs
    )


class TestDashboardSummary:
    def _make(self, **kwargs) -> dict:
        defaults = dict(
            date_from=_TODAY,
            date_to=_TODAY,
            budgets=_make_budget_stats(),
            work_orders=_make_work_order_stats(),
            invoices=_make_invoice_stats(),
            purchase_orders=_make_po_stats(),
            site_visits=_make_sv_stats(),
            monthly_revenue=[],
            top_customers=[],
            overdue_invoices=[],
            pending_budgets=[],
            low_stock_items_count=0,
            recent_activity=[],
        )
        defaults.update(kwargs)
        return defaults

    def test_valid_empty(self):
        s = DashboardSummary(**self._make())
        assert s.date_from == _TODAY
        assert s.low_stock_items_count == 0
        assert s.monthly_revenue == []

    def test_with_nested_lists(self):
        revenue = [
            MonthlyRevenue(month="2025-06", label="Jun 25",
                           invoiced=Decimal("1000"), collected=Decimal("800")),
        ]
        s = DashboardSummary(**self._make(monthly_revenue=revenue))
        assert len(s.monthly_revenue) == 1
        assert s.monthly_revenue[0].month == "2025-06"

    def test_with_top_customers(self):
        customers = [
            TopCustomer(customer_id=str(uuid.uuid4()),
                        customer_name="ABC", invoiced=Decimal("5000"), invoice_count=3),
        ]
        s = DashboardSummary(**self._make(top_customers=customers))
        assert len(s.top_customers) == 1

    def test_with_overdue_invoices(self):
        overdue = [
            OverdueInvoiceItem(
                id=str(uuid.uuid4()),
                invoice_number="FAC-001",
                customer_name="Test",
                total=Decimal("1000"),
                pending_amount=Decimal("1000"),
                days_overdue=15,
            )
        ]
        s = DashboardSummary(**self._make(overdue_invoices=overdue))
        assert len(s.overdue_invoices) == 1

    def test_with_pending_budgets(self):
        pending = [
            PendingBudgetItem(
                id=str(uuid.uuid4()),
                budget_number="PRES-001",
                customer_name="Test",
                total=Decimal("2000"),
                days_since_sent=5,
            )
        ]
        s = DashboardSummary(**self._make(pending_budgets=pending))
        assert len(s.pending_budgets) == 1

    def test_low_stock_count(self):
        s = DashboardSummary(**self._make(low_stock_items_count=3))
        assert s.low_stock_items_count == 3

    def test_date_range(self):
        d_from = date(2025, 1, 1)
        d_to = date(2025, 6, 30)
        s = DashboardSummary(**self._make(date_from=d_from, date_to=d_to))
        assert s.date_from == d_from
        assert s.date_to == d_to

    def test_missing_budgets_stats(self):
        data = self._make()
        del data["budgets"]
        with pytest.raises(ValidationError):
            DashboardSummary(**data)

    def test_recent_activity_items(self):
        activity = [
            RecentActivityItem(
                id=str(uuid.uuid4()),
                entity_type="work_order",
                entity_number="OBR-001",
                customer_name="Cliente Test",
                status="active",
                date=_NOW,
            )
        ]
        s = DashboardSummary(**self._make(recent_activity=activity))
        assert s.recent_activity[0].entity_type == "work_order"
