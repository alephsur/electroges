"""
Unit tests for BudgetService.

All repositories and the session are mocked — no database needed.
Covers: list/detail, create, update, status state machine,
        versioning, acceptance flow, line management, and totals calculation.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.budget import BudgetStatus
from app.schemas.budget import (
    BudgetCreate,
    BudgetLineCreate,
    BudgetLineUpdate,
    BudgetUpdate,
    ReorderLinesRequest,
)
from app.services.budget import BudgetService

TENANT_ID = uuid.uuid4()


# ── Factories ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_company(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a CompanySettings model instance."""
    c = MagicMock()
    c.default_tax_rate = Decimal("21.00")
    c.default_validity_days = 30
    c.name = "ElectroGes S.L."
    c.logo_path = None
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def make_line(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a BudgetLine model instance."""
    line = MagicMock()
    line.id = uuid.uuid4()
    line.budget_id = uuid.uuid4()
    line_type_mock = MagicMock()
    line_type_mock.value = "labor"
    line.line_type = line_type_mock
    line.sort_order = 0
    line.description = "Instalación eléctrica"
    line.inventory_item_id = None
    line.inventory_item = None
    line.quantity = Decimal("8.0")
    line.unit = "h"
    line.unit_price = Decimal("50.00")
    line.unit_cost = Decimal("30.00")
    line.line_discount_pct = Decimal("0.00")
    line.created_at = _now()
    line.updated_at = _now()
    for k, v in kwargs.items():
        setattr(line, k, v)
    return line


def make_budget(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a Budget model instance."""
    b = MagicMock()
    b.id = uuid.uuid4()
    b.tenant_id = TENANT_ID
    b.budget_number = "PRES-2026-0001"
    b.version = 1
    b.parent_budget_id = None
    b.is_latest_version = True
    b.customer_id = uuid.uuid4()
    b.customer = MagicMock()
    b.customer.name = "Cliente Test"
    b.customer.addresses = []
    b.site_visit_id = None
    b.status = BudgetStatus.DRAFT
    b.issue_date = date.today()
    b.valid_until = date.today() + timedelta(days=30)
    b.tax_rate = Decimal("21.00")
    b.discount_pct = Decimal("0.00")
    b.notes = None
    b.client_notes = None
    b.pdf_path = None
    b.work_order_id = None
    b.lines = []
    b.child_budgets = []
    b.created_at = _now()
    b.updated_at = _now()
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def make_budget_with_lines(
    status: BudgetStatus = BudgetStatus.DRAFT,
    tax_rate: Decimal = Decimal("21.00"),
    discount_pct: Decimal = Decimal("0.00"),
) -> MagicMock:
    """Return a budget mock pre-loaded with one labor line for totals testing."""
    labor_line = make_line(
        quantity=Decimal("8.0"),
        unit_price=Decimal("50.00"),
        unit_cost=Decimal("30.00"),
        line_discount_pct=Decimal("0.00"),
    )
    labor_line.line_type.value = "labor"
    return make_budget(
        status=status,
        tax_rate=tax_rate,
        discount_pct=discount_pct,
        lines=[labor_line],
    )


def make_inventory_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = uuid.uuid4()
    item.name = "Cable 2.5mm²"
    item.unit = "m"
    item.unit_price = Decimal("1.20")
    item.unit_cost = Decimal("0.80")
    item.unit_cost_avg = Decimal("0.82")
    item.stock_current = Decimal("100")
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item


def make_visit_mock(**kwargs) -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    v.customer_id = uuid.uuid4()
    v.status = MagicMock()
    v.status.value = "completed"
    v.estimated_hours = None
    v.materials = []
    for k, vv in kwargs.items():
        setattr(v, k, vv)
    return v


# ── NamedTuple fixture container ───────────────────────────────────────────────

class _Mocks(NamedTuple):
    svc: BudgetService
    repo: AsyncMock
    line_repo: AsyncMock
    company_repo: AsyncMock
    customer_repo: AsyncMock
    item_repo: AsyncMock
    visit_repo: AsyncMock


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mocks(mock_session) -> _Mocks:
    """
    Patches all repositories injected by BudgetService.__init__.
    Returns a typed NamedTuple so tests can reference repos by name.
    """
    repo = AsyncMock()
    line_repo = AsyncMock()
    company_repo = AsyncMock()
    customer_repo = AsyncMock()
    item_repo = AsyncMock()
    visit_repo = AsyncMock()

    company_repo.get.return_value = make_company()
    repo.get_next_budget_number.return_value = "PRES-2026-0001"

    with (
        patch("app.services.budget.BudgetRepository", return_value=repo),
        patch("app.services.budget.BudgetLineRepository", return_value=line_repo),
        patch("app.services.budget.CompanySettingsRepository", return_value=company_repo),
        patch("app.services.budget.CustomerRepository", return_value=customer_repo),
        patch("app.services.budget.InventoryItemRepository", return_value=item_repo),
        patch("app.services.budget.SiteVisitRepository", return_value=visit_repo),
    ):
        svc = BudgetService(mock_session, TENANT_ID)
        yield _Mocks(svc, repo, line_repo, company_repo, customer_repo, item_repo, visit_repo)


# ── list_budgets ───────────────────────────────────────────────────────────────

class TestListBudgets:
    async def test_returns_paginated_response(self, mocks):
        b1 = make_budget_with_lines()
        b2 = make_budget_with_lines()
        mocks.repo.search.return_value = ([b1, b2], 2)

        result = await mocks.svc.list_budgets(
            q=None, customer_id=None, status_filter=None,
            date_from=None, date_to=None, latest_only=True,
            skip=0, limit=10,
        )

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 10

    async def test_empty_result(self, mocks):
        mocks.repo.search.return_value = ([], 0)

        result = await mocks.svc.list_budgets(
            q=None, customer_id=None, status_filter=None,
            date_from=None, date_to=None, latest_only=True,
            skip=0, limit=10,
        )

        assert result.total == 0
        assert result.items == []

    async def test_passes_all_filters_to_repo(self, mocks):
        mocks.repo.search.return_value = ([], 0)
        customer_id = uuid.uuid4()
        date_from = date(2026, 1, 1)
        date_to = date(2026, 12, 31)

        await mocks.svc.list_budgets(
            q="PRES-2026",
            customer_id=customer_id,
            status_filter="draft",
            date_from=date_from,
            date_to=date_to,
            latest_only=False,
            skip=5,
            limit=20,
        )

        mocks.repo.search.assert_called_once_with(
            query="PRES-2026",
            customer_id=customer_id,
            status="draft",
            date_from=date_from,
            date_to=date_to,
            latest_only=False,
            skip=5,
            limit=20,
        )

    async def test_summary_contains_expected_fields(self, mocks):
        budget = make_budget_with_lines()
        mocks.repo.search.return_value = ([budget], 1)

        result = await mocks.svc.list_budgets(
            q=None, customer_id=None, status_filter=None,
            date_from=None, date_to=None, latest_only=True,
            skip=0, limit=10,
        )

        summary = result.items[0]
        assert summary.budget_number == budget.budget_number
        assert summary.version == budget.version
        assert summary.status == budget.status.value


# ── get_budget ─────────────────────────────────────────────────────────────────

class TestGetBudget:
    async def test_returns_response(self, mocks):
        budget = make_budget_with_lines()
        mocks.repo.get_with_full_detail.return_value = budget

        result = await mocks.svc.get_budget(budget.id)

        assert result.id == budget.id
        assert result.budget_number == budget.budget_number

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_budget(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_budget_response_has_totals(self, mocks):
        budget = make_budget_with_lines(tax_rate=Decimal("21.00"))
        mocks.repo.get_with_full_detail.return_value = budget

        result = await mocks.svc.get_budget(budget.id)

        assert result.totals is not None
        assert result.totals.total > 0

    async def test_budget_response_has_lines(self, mocks):
        budget = make_budget_with_lines()
        mocks.repo.get_with_full_detail.return_value = budget

        result = await mocks.svc.get_budget(budget.id)

        assert len(result.lines) == 1


# ── create_budget ──────────────────────────────────────────────────────────────

class TestCreateBudget:
    async def test_creates_budget_without_customer(self, mocks):
        new_budget = make_budget()
        mocks.repo.create.return_value = new_budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        data = BudgetCreate()

        result = await mocks.svc.create_budget(data)

        mocks.repo.create.assert_called_once()
        assert result is not None

    async def test_creates_budget_with_valid_customer(self, mocks):
        customer_id = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = customer_id
        mocks.customer_repo.get_by_id.return_value = customer_mock

        new_budget = make_budget(customer_id=customer_id)
        mocks.repo.create.return_value = new_budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        data = BudgetCreate(customer_id=customer_id)
        result = await mocks.svc.create_budget(data)

        mocks.customer_repo.get_by_id.assert_called_once_with(customer_id)
        assert result is not None

    async def test_raises_404_for_unknown_customer(self, mocks):
        mocks.customer_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_budget(BudgetCreate(customer_id=uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert "Cliente" in exc_info.value.detail

    async def test_budget_number_generated_from_repo(self, mocks):
        mocks.repo.get_next_budget_number.return_value = "PRES-2026-0042"
        created = make_budget(budget_number="PRES-2026-0042")
        mocks.repo.create.return_value = created
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        await mocks.svc.create_budget(BudgetCreate())

        mocks.repo.get_next_budget_number.assert_called_once()

    async def test_uses_company_defaults_for_dates_and_tax(self, mocks):
        company = make_company(default_tax_rate=Decimal("10.00"), default_validity_days=15)
        mocks.company_repo.get.return_value = company
        new_budget = make_budget()
        mocks.repo.create.return_value = new_budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        await mocks.svc.create_budget(BudgetCreate())

        # Budget instance passed to create() should have tax_rate from company
        call_args = mocks.repo.create.call_args
        budget_arg = call_args[0][0]
        assert budget_arg.tax_rate == Decimal("10.00")

    async def test_uses_explicit_tax_rate_over_company_default(self, mocks):
        mocks.repo.create.return_value = make_budget()
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        await mocks.svc.create_budget(BudgetCreate(tax_rate=Decimal("4.00")))

        call_args = mocks.repo.create.call_args
        budget_arg = call_args[0][0]
        assert budget_arg.tax_rate == Decimal("4.00")

    async def test_creates_lines_for_each_line_in_data(self, mocks):
        mocks.repo.create.return_value = make_budget()
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()
        mocks.line_repo.create.return_value = make_line()

        data = BudgetCreate(
            lines=[
                BudgetLineCreate(
                    line_type="labor",
                    description="Trabajo 1",
                    quantity=Decimal("4"),
                    unit_price=Decimal("50.00"),
                ),
                BudgetLineCreate(
                    line_type="material",
                    description="Material 1",
                    quantity=Decimal("10"),
                    unit_price=Decimal("2.00"),
                ),
            ]
        )
        await mocks.svc.create_budget(data)

        assert mocks.line_repo.create.call_count == 2

    async def test_session_commit_called(self, mocks, mock_session):
        mocks.repo.create.return_value = make_budget()
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        await mocks.svc.create_budget(BudgetCreate())

        mock_session.commit.assert_called()


# ── update_budget ──────────────────────────────────────────────────────────────

class TestUpdateBudget:
    async def test_updates_draft_budget(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT)
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        result = await mocks.svc.update_budget(
            budget.id, BudgetUpdate(notes="Nota actualizada")
        )

        mocks.repo.update.assert_called_once_with(budget, {"notes": "Nota actualizada"})
        assert result is not None

    async def test_raises_404_when_budget_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_budget(uuid.uuid4(), BudgetUpdate())

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_budget_not_draft(self, mocks):
        for status in (BudgetStatus.SENT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status)
            mocks.repo.get_by_id.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.update_budget(budget.id, BudgetUpdate(notes="nuevo"))

            assert exc_info.value.status_code == 400

    async def test_excludes_none_values_from_update(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT)
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        await mocks.svc.update_budget(
            budget.id,
            BudgetUpdate(notes="Solo nota", valid_until=None),
        )

        call_kwargs = mocks.repo.update.call_args[0][1]
        assert "valid_until" not in call_kwargs
        assert call_kwargs["notes"] == "Solo nota"


# ── send_budget ────────────────────────────────────────────────────────────────

class TestSendBudget:
    async def test_sends_draft_budget_with_lines(self, mocks):
        budget = make_budget_with_lines(status=BudgetStatus.DRAFT)
        mocks.repo.get_with_full_detail.return_value = budget
        mocks.repo.get_with_full_detail.side_effect = [budget, make_budget_with_lines(status=BudgetStatus.SENT)]

        await mocks.svc.send_budget(budget.id)

        # update was called with SENT status
        update_call = mocks.repo.update.call_args
        assert update_call[0][1]["status"] == BudgetStatus.SENT

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.send_budget(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks):
        for status in (BudgetStatus.SENT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status, lines=[make_line()])
            mocks.repo.get_with_full_detail.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.send_budget(budget.id)

            assert exc_info.value.status_code == 400

    async def test_raises_400_when_no_lines(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT, lines=[])
        mocks.repo.get_with_full_detail.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.send_budget(budget.id)

        assert exc_info.value.status_code == 400
        assert "líneas" in exc_info.value.detail


# ── reject_budget ──────────────────────────────────────────────────────────────

class TestRejectBudget:
    async def test_rejects_sent_budget(self, mocks):
        budget = make_budget(status=BudgetStatus.SENT)
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines(status=BudgetStatus.REJECTED)

        await mocks.svc.reject_budget(budget.id, notes=None)

        update_call = mocks.repo.update.call_args
        assert update_call[0][1]["status"] == BudgetStatus.REJECTED

    async def test_appends_rejection_notes_when_provided(self, mocks):
        budget = make_budget(status=BudgetStatus.SENT, notes="Nota previa")
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines(status=BudgetStatus.REJECTED)

        await mocks.svc.reject_budget(budget.id, notes="Precio muy alto")

        update_call = mocks.repo.update.call_args
        notes_value = update_call[0][1]["notes"]
        assert "Rechazo" in notes_value
        assert "Precio muy alto" in notes_value

    async def test_does_not_touch_notes_when_none(self, mocks):
        budget = make_budget(status=BudgetStatus.SENT, notes="Nota previa")
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines(status=BudgetStatus.REJECTED)

        await mocks.svc.reject_budget(budget.id, notes=None)

        update_call = mocks.repo.update.call_args
        assert "notes" not in update_call[0][1]

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reject_budget(uuid.uuid4(), notes=None)

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_sent(self, mocks):
        for status in (BudgetStatus.DRAFT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status)
            mocks.repo.get_by_id.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.reject_budget(budget.id, notes=None)

            assert exc_info.value.status_code == 400


# ── create_new_version ─────────────────────────────────────────────────────────

class TestCreateNewVersion:
    async def test_creates_version_from_sent_budget(self, mocks):
        original = make_budget_with_lines(status=BudgetStatus.SENT)
        original.budget_number = "PRES-2026-0001"
        original.version = 1
        original.parent_budget_id = None

        new_budget = make_budget(version=2, budget_number="PRES-2026-0001-v2")
        mocks.repo.get_with_full_detail.side_effect = [original, make_budget_with_lines()]
        mocks.repo.create.return_value = new_budget
        mocks.line_repo.create.return_value = make_line()

        result = await mocks.svc.create_new_version(original.id)

        mocks.repo.mark_previous_versions_outdated.assert_called_once_with(original.id)
        mocks.repo.create.assert_called_once()

        created_budget = mocks.repo.create.call_args[0][0]
        assert created_budget.version == 2
        assert created_budget.budget_number == "PRES-2026-0001-v2"

    async def test_creates_version_from_rejected_budget(self, mocks):
        original = make_budget_with_lines(status=BudgetStatus.REJECTED)
        original.budget_number = "PRES-2026-0001"
        original.version = 1
        original.parent_budget_id = None

        new_budget = make_budget(version=2)
        mocks.repo.get_with_full_detail.side_effect = [original, make_budget_with_lines()]
        mocks.repo.create.return_value = new_budget
        mocks.line_repo.create.return_value = make_line()

        await mocks.svc.create_new_version(original.id)

        mocks.repo.create.assert_called_once()

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_new_version(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_draft(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT)
        mocks.repo.get_with_full_detail.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_new_version(budget.id)

        assert exc_info.value.status_code == 400

    async def test_raises_400_when_accepted(self, mocks):
        budget = make_budget(status=BudgetStatus.ACCEPTED)
        mocks.repo.get_with_full_detail.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_new_version(budget.id)

        assert exc_info.value.status_code == 400

    async def test_copies_all_lines_from_original(self, mocks):
        line1 = make_line(description="Trabajo 1")
        line1.line_type.value = "labor"
        line2 = make_line(description="Material 1")
        line2.line_type.value = "material"
        original = make_budget(status=BudgetStatus.SENT, lines=[line1, line2])
        original.budget_number = "PRES-2026-0001"
        original.version = 1
        original.parent_budget_id = None

        new_budget = make_budget(version=2)
        mocks.repo.get_with_full_detail.side_effect = [original, make_budget_with_lines()]
        mocks.repo.create.return_value = new_budget
        mocks.line_repo.create.return_value = make_line()

        await mocks.svc.create_new_version(original.id)

        # Two lines should be created for the new version
        assert mocks.line_repo.create.call_count == 2

    async def test_version_number_is_parent_plus_one(self, mocks):
        original = make_budget_with_lines(status=BudgetStatus.SENT)
        original.budget_number = "PRES-2026-0001-v2"
        original.version = 2
        original.parent_budget_id = uuid.uuid4()

        new_budget = make_budget(version=3)
        mocks.repo.get_with_full_detail.side_effect = [original, make_budget_with_lines()]
        mocks.repo.create.return_value = new_budget
        mocks.line_repo.create.return_value = make_line()

        await mocks.svc.create_new_version(original.id)

        created_budget = mocks.repo.create.call_args[0][0]
        assert created_budget.version == 3
        assert created_budget.budget_number == "PRES-2026-0001-v3"

    async def test_root_id_is_own_id_when_no_parent(self, mocks):
        """When versioning a root budget, new version's parent_budget_id must be its own id."""
        own_id = uuid.uuid4()
        original = make_budget_with_lines(status=BudgetStatus.SENT)
        original.id = own_id
        original.budget_number = "PRES-2026-0005"
        original.version = 1
        original.parent_budget_id = None

        new_budget = make_budget(version=2)
        mocks.repo.get_with_full_detail.side_effect = [original, make_budget_with_lines()]
        mocks.repo.create.return_value = new_budget
        mocks.line_repo.create.return_value = make_line()

        await mocks.svc.create_new_version(original.id)

        created_budget = mocks.repo.create.call_args[0][0]
        assert created_budget.parent_budget_id == own_id


# ── get_work_order_preview ─────────────────────────────────────────────────────

class TestGetWorkOrderPreview:
    def _make_labor_line(self) -> MagicMock:
        line = make_line(
            quantity=Decimal("8"),
            unit_cost=Decimal("30.00"),
            description="Instalación",
        )
        line.line_type.value = "labor"
        return line

    def _make_material_line(self, stock: Decimal = Decimal("100")) -> MagicMock:
        item = make_inventory_item(stock_current=stock)
        line = make_line(
            quantity=Decimal("10"),
            unit_cost=Decimal("0.80"),
            description="Cable 2.5mm²",
        )
        line.line_type.value = "material"
        line.inventory_item = item
        line.inventory_item_id = item.id
        line.unit = "m"
        return line

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_work_order_preview(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_sent(self, mocks):
        for status in (BudgetStatus.DRAFT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status)
            mocks.repo.get_with_full_detail.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.get_work_order_preview(budget.id)

            assert exc_info.value.status_code == 400

    async def test_preview_contains_labor_tasks(self, mocks):
        labor_line = self._make_labor_line()
        budget = make_budget(status=BudgetStatus.SENT, lines=[labor_line])
        mocks.repo.get_with_full_detail.return_value = budget

        preview = await mocks.svc.get_work_order_preview(budget.id)

        assert len(preview.tasks_to_create) == 1
        task = preview.tasks_to_create[0]
        assert task["name"] == "Instalación"
        assert task["estimated_hours"] == 8.0

    async def test_preview_contains_material_reservations(self, mocks):
        mat_line = self._make_material_line(stock=Decimal("100"))
        budget = make_budget(status=BudgetStatus.SENT, lines=[mat_line])
        mocks.repo.get_with_full_detail.return_value = budget

        preview = await mocks.svc.get_work_order_preview(budget.id)

        assert len(preview.materials_to_reserve) == 1
        mat = preview.materials_to_reserve[0]
        assert mat["quantity"] == 10.0
        assert mat["enough_stock"] is True
        assert preview.warnings == []

    async def test_preview_warns_on_insufficient_stock(self, mocks):
        mat_line = self._make_material_line(stock=Decimal("5"))
        budget = make_budget(status=BudgetStatus.SENT, lines=[mat_line])
        mocks.repo.get_with_full_detail.return_value = budget

        preview = await mocks.svc.get_work_order_preview(budget.id)

        mat = preview.materials_to_reserve[0]
        assert mat["enough_stock"] is False
        assert len(preview.warnings) == 1
        assert "insuficiente" in preview.warnings[0]

    async def test_preview_total_estimated_cost(self, mocks):
        labor_line = self._make_labor_line()  # 8h * 30 = 240
        mat_line = self._make_material_line()   # 10m * 0.80 = 8
        budget = make_budget(status=BudgetStatus.SENT, lines=[labor_line, mat_line])
        mocks.repo.get_with_full_detail.return_value = budget

        preview = await mocks.svc.get_work_order_preview(budget.id)

        assert float(preview.total_estimated_cost) == pytest.approx(248.0)

    async def test_preview_has_correct_budget_info(self, mocks):
        budget = make_budget(status=BudgetStatus.SENT, lines=[self._make_labor_line()])
        budget.budget_number = "PRES-2026-0099"
        mocks.repo.get_with_full_detail.return_value = budget

        preview = await mocks.svc.get_work_order_preview(budget.id)

        assert preview.budget_number == "PRES-2026-0099"
        assert preview.customer_name == budget.customer.name


# ── accept_and_create_work_order ───────────────────────────────────────────────

class TestAcceptAndCreateWorkOrder:
    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.accept_and_create_work_order(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_sent(self, mocks):
        for status in (BudgetStatus.DRAFT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status)
            mocks.repo.get_by_id.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.accept_and_create_work_order(budget.id)

            assert exc_info.value.status_code == 400

    async def test_marks_budget_as_accepted_and_creates_work_order(self, mocks, mock_session):
        budget = make_budget(status=BudgetStatus.SENT)
        mocks.repo.get_by_id.return_value = budget

        wo_mock = MagicMock()
        wo_mock.id = uuid.uuid4()
        wo_mock.work_order_number = "OT-2026-0001"

        work_order_svc_mock = AsyncMock()
        work_order_svc_mock.create_from_budget.return_value = wo_mock

        with patch("app.services.work_order.WorkOrderService", return_value=work_order_svc_mock):
            result = await mocks.svc.accept_and_create_work_order(budget.id)

        mocks.repo.update.assert_called_once_with(budget, {"status": BudgetStatus.ACCEPTED})
        assert result["status"] == "accepted"
        assert result["work_order_number"] == "OT-2026-0001"
        assert "work_order_id" in result

    async def test_result_contains_expected_keys(self, mocks):
        budget = make_budget(status=BudgetStatus.SENT)
        mocks.repo.get_by_id.return_value = budget

        wo_mock = MagicMock()
        wo_mock.id = uuid.uuid4()
        wo_mock.work_order_number = "OT-2026-0001"

        work_order_svc_mock = AsyncMock()
        work_order_svc_mock.create_from_budget.return_value = wo_mock

        with patch("app.services.work_order.WorkOrderService", return_value=work_order_svc_mock):
            result = await mocks.svc.accept_and_create_work_order(budget.id)

        assert "budget_id" in result
        assert "work_order_id" in result
        assert "message" in result


# ── add_line ───────────────────────────────────────────────────────────────────

class TestAddLine:
    async def test_adds_line_to_draft_budget(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT)
        mocks.repo.get_by_id.return_value = budget
        new_line = make_line()
        mocks.line_repo.create.return_value = new_line

        line_data = BudgetLineCreate(
            line_type="labor",
            description="Nuevo trabajo",
            quantity=Decimal("4"),
            unit_price=Decimal("60.00"),
        )
        result = await mocks.svc.add_line(budget.id, line_data)

        mocks.line_repo.create.assert_called_once()
        assert result is not None

    async def test_raises_404_when_budget_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_line(
                uuid.uuid4(),
                BudgetLineCreate(
                    line_type="labor",
                    description="Trabajo",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                ),
            )

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks):
        for status in (BudgetStatus.SENT, BudgetStatus.ACCEPTED, BudgetStatus.REJECTED):
            budget = make_budget(status=status)
            mocks.repo.get_by_id.return_value = budget

            with pytest.raises(HTTPException) as exc_info:
                await mocks.svc.add_line(
                    budget.id,
                    BudgetLineCreate(
                        line_type="labor",
                        description="Trabajo",
                        quantity=Decimal("1"),
                        unit_price=Decimal("50.00"),
                    ),
                )

            assert exc_info.value.status_code == 400

    async def test_material_line_autofills_unit_and_cost_from_inventory(self, mocks):
        budget = make_budget(status=BudgetStatus.DRAFT)
        mocks.repo.get_by_id.return_value = budget
        item_id = uuid.uuid4()
        item = make_inventory_item(unit="m", unit_cost=Decimal("1.00"), unit_cost_avg=Decimal("1.10"))
        item.id = item_id
        mocks.item_repo.get_by_id.return_value = item

        new_line = make_line()
        mocks.line_repo.create.return_value = new_line

        line_data = BudgetLineCreate(
            line_type="material",
            description="Cable",
            inventory_item_id=item_id,
            quantity=Decimal("20"),
            unit_price=Decimal("1.50"),
            unit_cost=Decimal("0.0"),  # default → should be filled from item
        )
        await mocks.svc.add_line(budget.id, line_data)

        created_line_arg = mocks.line_repo.create.call_args[0][0]
        # unit_cost_avg from item should be used
        assert created_line_arg.unit_cost == item.unit_cost_avg
        assert created_line_arg.unit == item.unit


# ── update_line ────────────────────────────────────────────────────────────────

class TestUpdateLine:
    async def test_updates_line_in_draft_budget(self, mocks):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.DRAFT)
        budget.id = budget_id

        line = make_line()
        line.budget_id = budget_id

        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = budget
        mocks.line_repo.create.return_value = line  # for refresh

        result = await mocks.svc.update_line(
            budget_id, line.id, BudgetLineUpdate(description="Trabajo actualizado")
        )

        mocks.line_repo.update.assert_called_once()
        assert result is not None

    async def test_raises_404_when_line_not_found(self, mocks):
        mocks.line_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(
                uuid.uuid4(), uuid.uuid4(), BudgetLineUpdate(description="X")
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_line_belongs_to_different_budget(self, mocks):
        line = make_line()
        line.budget_id = uuid.uuid4()  # different from the budget_id passed

        mocks.line_repo.get_by_id.return_value = line

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(
                uuid.uuid4(),  # different budget_id
                line.id,
                BudgetLineUpdate(description="X"),
            )

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_budget_not_draft(self, mocks):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.SENT)
        budget.id = budget_id

        line = make_line()
        line.budget_id = budget_id

        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(
                budget_id, line.id, BudgetLineUpdate(description="X")
            )

        assert exc_info.value.status_code == 400


# ── delete_line ────────────────────────────────────────────────────────────────

class TestDeleteLine:
    async def test_deletes_line_from_draft_budget(self, mocks):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.DRAFT)
        budget.id = budget_id

        line = make_line()
        line.budget_id = budget_id

        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = budget

        await mocks.svc.delete_line(budget_id, line.id)

        mocks.line_repo.delete.assert_called_once_with(line)

    async def test_raises_404_when_line_not_found(self, mocks):
        mocks.line_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_line_belongs_to_different_budget(self, mocks):
        line = make_line()
        line.budget_id = uuid.uuid4()
        mocks.line_repo.get_by_id.return_value = line

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(uuid.uuid4(), line.id)

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.SENT)
        budget.id = budget_id
        line = make_line()
        line.budget_id = budget_id

        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(budget_id, line.id)

        assert exc_info.value.status_code == 400


# ── reorder_lines ──────────────────────────────────────────────────────────────

class TestReorderLines:
    async def test_reorders_lines(self, mocks, mock_session):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.DRAFT)
        budget.id = budget_id
        mocks.repo.get_by_id.return_value = budget
        mocks.repo.get_with_full_detail.return_value = make_budget_with_lines()

        ids = [uuid.uuid4(), uuid.uuid4()]
        await mocks.svc.reorder_lines(budget_id, ReorderLinesRequest(line_ids=ids))

        mock_session.execute.assert_called()

    async def test_raises_404_when_budget_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reorder_lines(
                uuid.uuid4(), ReorderLinesRequest(line_ids=[uuid.uuid4()])
            )

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks):
        budget_id = uuid.uuid4()
        budget = make_budget(status=BudgetStatus.SENT)
        budget.id = budget_id
        mocks.repo.get_by_id.return_value = budget

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reorder_lines(
                budget_id, ReorderLinesRequest(line_ids=[uuid.uuid4()])
            )

        assert exc_info.value.status_code == 400


# ── _calculate_totals (via get_budget) ─────────────────────────────────────────

class TestCalculateTotals:
    """
    Tests for the _calculate_totals internal helper.
    Accessed indirectly via _build_response which is called by get_budget.
    """

    def _svc(self, mock_session) -> BudgetService:
        """Instantiate a bare service — repos won't be called for pure calc tests."""
        with (
            patch("app.services.budget.BudgetRepository"),
            patch("app.services.budget.BudgetLineRepository"),
            patch("app.services.budget.CompanySettingsRepository"),
            patch("app.services.budget.CustomerRepository"),
            patch("app.services.budget.InventoryItemRepository"),
            patch("app.services.budget.SiteVisitRepository"),
        ):
            return BudgetService(mock_session, TENANT_ID)

    def _make_line(
        self,
        quantity: str,
        unit_price: str,
        unit_cost: str,
        line_discount_pct: str = "0.00",
    ) -> MagicMock:
        line = MagicMock()
        line.quantity = Decimal(quantity)
        line.unit_price = Decimal(unit_price)
        line.unit_cost = Decimal(unit_cost)
        line.line_discount_pct = Decimal(line_discount_pct)
        return line

    def test_basic_totals_no_discount_no_tax_reduction(self, mock_session):
        svc = self._svc(mock_session)
        line = self._make_line("10", "100.00", "60.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        # subtotal = 10 * 100 = 1000
        # discount = 0
        # taxable_base = 1000
        # tax = 1000 * 0.21 = 210
        # total = 1210
        assert float(totals.subtotal_before_discount) == pytest.approx(1000.00)
        assert float(totals.discount_amount) == pytest.approx(0.00)
        assert float(totals.taxable_base) == pytest.approx(1000.00)
        assert float(totals.tax_amount) == pytest.approx(210.00)
        assert float(totals.total) == pytest.approx(1210.00)

    def test_totals_with_global_discount(self, mock_session):
        svc = self._svc(mock_session)
        line = self._make_line("10", "100.00", "60.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("10.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        # subtotal = 1000, discount 10% = 100
        # taxable_base = 900, tax = 189, total = 1089
        assert float(totals.subtotal_before_discount) == pytest.approx(1000.00)
        assert float(totals.discount_amount) == pytest.approx(100.00)
        assert float(totals.taxable_base) == pytest.approx(900.00)
        assert float(totals.tax_amount) == pytest.approx(189.00)
        assert float(totals.total) == pytest.approx(1089.00)

    def test_totals_with_line_discount(self, mock_session):
        svc = self._svc(mock_session)
        # Line discount: 10 * 100 * (1 - 0.20) = 800
        line = self._make_line("10", "100.00", "60.00", line_discount_pct="20.00")
        budget = make_budget(tax_rate=Decimal("0.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert float(totals.subtotal_before_discount) == pytest.approx(800.00)

    def test_totals_with_zero_tax(self, mock_session):
        svc = self._svc(mock_session)
        line = self._make_line("5", "200.00", "100.00")
        budget = make_budget(tax_rate=Decimal("0.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert float(totals.tax_amount) == pytest.approx(0.00)
        assert float(totals.total) == pytest.approx(1000.00)

    def test_total_cost_sums_all_line_costs(self, mock_session):
        svc = self._svc(mock_session)
        line1 = self._make_line("4", "50.00", "30.00")   # cost = 120
        line2 = self._make_line("10", "2.00", "1.00")    # cost = 10
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line1, line2])

        totals = svc._calculate_totals(budget)

        assert float(totals.total_cost) == pytest.approx(130.00)

    def test_gross_margin_calculation(self, mock_session):
        svc = self._svc(mock_session)
        # total = 1210 (from first test), total_cost = 600
        # gross_margin = 1210 - 600 = 610
        # gross_margin_pct = 610 / 1210 * 100 ≈ 50.41%
        line = self._make_line("10", "100.00", "60.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert float(totals.gross_margin) == pytest.approx(610.00)
        assert float(totals.gross_margin_pct) == pytest.approx(50.41, abs=0.05)

    def test_empty_lines_returns_zeros(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[])

        totals = svc._calculate_totals(budget)

        assert float(totals.subtotal_before_discount) == 0.0
        assert float(totals.total) == 0.0
        assert float(totals.gross_margin) == 0.0

    def test_margin_status_green_above_25(self, mock_session):
        svc = self._svc(mock_session)
        # margin_pct > 25 → green
        # unit_price=100, unit_cost=50 → total=121, cost=50, margin=71, margin_pct≈58.7%
        line = self._make_line("1", "100.00", "50.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert totals.margin_status == "green"

    def test_margin_status_amber_between_15_and_25(self, mock_session):
        svc = self._svc(mock_session)
        # We need gross_margin_pct between 15 and 25.
        # total = 121 (price=100, tax=21%), cost=95
        # gross_margin = 121-95=26, margin_pct = 26/121 ≈ 21.5% → amber
        line = self._make_line("1", "100.00", "95.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert totals.margin_status == "amber"

    def test_margin_status_red_below_15(self, mock_session):
        svc = self._svc(mock_session)
        # total = 121 (price=100, tax=21%), cost=110
        # gross_margin = 121-110=11, margin_pct = 11/121 ≈ 9.1% → red
        line = self._make_line("1", "100.00", "110.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line])

        totals = svc._calculate_totals(budget)

        assert totals.margin_status == "red"

    def test_margin_status_red_when_total_is_zero(self, mock_session):
        svc = self._svc(mock_session)
        # Zero total → margin_pct = 0 → red
        budget = make_budget(tax_rate=Decimal("0.00"), discount_pct=Decimal("0.00"), lines=[])

        totals = svc._calculate_totals(budget)

        assert totals.margin_status == "red"

    def test_multiple_lines_compound_correctly(self, mock_session):
        svc = self._svc(mock_session)
        # line1: 5 * 200 = 1000; line2: 10 * 50 = 500 → subtotal = 1500
        line1 = self._make_line("5", "200.00", "100.00")
        line2 = self._make_line("10", "50.00", "30.00")
        budget = make_budget(tax_rate=Decimal("21.00"), discount_pct=Decimal("0.00"), lines=[line1, line2])

        totals = svc._calculate_totals(budget)

        assert float(totals.subtotal_before_discount) == pytest.approx(1500.00)
        assert float(totals.tax_amount) == pytest.approx(315.00)
        assert float(totals.total) == pytest.approx(1815.00)


# ── _get_effective_status ──────────────────────────────────────────────────────

class TestGetEffectiveStatus:
    def _svc(self, mock_session) -> BudgetService:
        with (
            patch("app.services.budget.BudgetRepository"),
            patch("app.services.budget.BudgetLineRepository"),
            patch("app.services.budget.CompanySettingsRepository"),
            patch("app.services.budget.CustomerRepository"),
            patch("app.services.budget.InventoryItemRepository"),
            patch("app.services.budget.SiteVisitRepository"),
        ):
            return BudgetService(mock_session, TENANT_ID)

    def test_sent_and_not_expired_returns_sent(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(
            status=BudgetStatus.SENT,
            valid_until=date.today() + timedelta(days=10),
        )
        assert svc._get_effective_status(budget) == "sent"

    def test_sent_and_expired_returns_expired(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(
            status=BudgetStatus.SENT,
            valid_until=date.today() - timedelta(days=1),
        )
        assert svc._get_effective_status(budget) == "expired"

    def test_sent_expires_today_returns_sent(self, mock_session):
        """Expires on exactly today → NOT expired (valid_until == today, not <)."""
        svc = self._svc(mock_session)
        budget = make_budget(
            status=BudgetStatus.SENT,
            valid_until=date.today(),
        )
        # valid_until < today is False when equal
        assert svc._get_effective_status(budget) == "sent"

    def test_draft_returns_draft(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(status=BudgetStatus.DRAFT)
        assert svc._get_effective_status(budget) == "draft"

    def test_accepted_returns_accepted(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(status=BudgetStatus.ACCEPTED)
        assert svc._get_effective_status(budget) == "accepted"

    def test_rejected_returns_rejected(self, mock_session):
        svc = self._svc(mock_session)
        budget = make_budget(status=BudgetStatus.REJECTED)
        assert svc._get_effective_status(budget) == "rejected"


# ── _build_line_response ───────────────────────────────────────────────────────

class TestBuildLineResponse:
    def _svc(self, mock_session) -> BudgetService:
        with (
            patch("app.services.budget.BudgetRepository"),
            patch("app.services.budget.BudgetLineRepository"),
            patch("app.services.budget.CompanySettingsRepository"),
            patch("app.services.budget.CustomerRepository"),
            patch("app.services.budget.InventoryItemRepository"),
            patch("app.services.budget.SiteVisitRepository"),
        ):
            return BudgetService(mock_session, TENANT_ID)

    def test_subtotal_no_discount(self, mock_session):
        svc = self._svc(mock_session)
        line = make_line(
            quantity=Decimal("4"),
            unit_price=Decimal("50.00"),
            unit_cost=Decimal("30.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_response(line)

        assert float(resp.subtotal) == pytest.approx(200.00)

    def test_subtotal_with_line_discount(self, mock_session):
        svc = self._svc(mock_session)
        # 4 * 50 * (1 - 0.10) = 180
        line = make_line(
            quantity=Decimal("4"),
            unit_price=Decimal("50.00"),
            unit_cost=Decimal("30.00"),
            line_discount_pct=Decimal("10.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_response(line)

        assert float(resp.subtotal) == pytest.approx(180.00)

    def test_margin_pct_zero_when_unit_price_is_zero(self, mock_session):
        svc = self._svc(mock_session)
        line = make_line(
            quantity=Decimal("1"),
            unit_price=Decimal("0.00"),
            unit_cost=Decimal("0.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_response(line)

        assert float(resp.margin_pct) == 0.0

    def test_margin_pct_calculated_correctly(self, mock_session):
        svc = self._svc(mock_session)
        # (100 - 60) / 100 * 100 = 40%
        line = make_line(
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("60.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_response(line)

        assert float(resp.margin_pct) == pytest.approx(40.00)

    def test_margin_amount_calculated_correctly(self, mock_session):
        svc = self._svc(mock_session)
        # (100 - 60) * 5 = 200
        line = make_line(
            quantity=Decimal("5"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("60.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_response(line)

        assert float(resp.margin_amount) == pytest.approx(200.00)

    def test_internal_response_includes_cost_fields(self, mock_session):
        svc = self._svc(mock_session)
        line = make_line(
            quantity=Decimal("2"),
            unit_price=Decimal("80.00"),
            unit_cost=Decimal("50.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "material"

        resp = svc._build_line_response(line)

        assert resp.unit_cost == Decimal("50.00")
        assert resp.margin_pct is not None
        assert resp.margin_amount is not None

    def test_public_response_does_not_include_cost_fields(self, mock_session):
        svc = self._svc(mock_session)
        line = make_line(
            quantity=Decimal("2"),
            unit_price=Decimal("80.00"),
            unit_cost=Decimal("50.00"),
            line_discount_pct=Decimal("0.00"),
        )
        line.line_type.value = "labor"

        resp = svc._build_line_public_response(line)

        assert not hasattr(resp, "unit_cost")
        assert not hasattr(resp, "margin_pct")
        assert not hasattr(resp, "margin_amount")
