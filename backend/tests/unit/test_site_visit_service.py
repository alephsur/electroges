"""
Unit tests for SiteVisitService.

All seven repositories and the session are mocked — no database needed.
Covers: list/detail, CRUD, status state machine, customer linking,
        materials, photos, and documents.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.site_visit import SiteVisitStatus
from app.schemas.site_visit import (
    SiteVisitCreate,
    SiteVisitLinkCustomer,
    SiteVisitMaterialCreate,
    SiteVisitMaterialUpdate,
    SiteVisitPhotoUpdate,
    SiteVisitStatusUpdate,
    SiteVisitUpdate,
)
from app.services.site_visit import SiteVisitService, _VALID_TRANSITIONS

TENANT_ID = uuid.uuid4()


# ── Factories ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_visit(**kwargs) -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    v.tenant_id = TENANT_ID
    v.customer_id = None
    v.customer = None
    v.customer_address_id = None
    v.customer_address = None
    v.address_text = "Calle Mayor 1, Madrid, 28001"
    v.contact_name = "Contacto de prueba"
    v.contact_phone = "600000001"
    v.visit_date = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)
    v.estimated_duration_hours = None
    v.status = SiteVisitStatus.SCHEDULED
    v.description = None
    v.work_scope = None
    v.technical_notes = None
    v.estimated_hours = None
    v.estimated_budget = None
    v.materials = []
    v.photos = []
    v.documents = []
    v.created_at = _now()
    v.updated_at = _now()
    for k, val in kwargs.items():
        setattr(v, k, val)
    return v


def make_customer_mock(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.name = "Cliente de prueba"
    c.customer_type = MagicMock()
    c.customer_type.value = "individual"
    for k, val in kwargs.items():
        setattr(c, k, val)
    return c


def make_address_mock(**kwargs) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.customer_id = uuid.uuid4()
    a.street = "Gran Vía 5"
    a.city = "Madrid"
    a.postal_code = "28013"
    a.province = None
    for k, val in kwargs.items():
        setattr(a, k, val)
    return a


def make_material(**kwargs) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.site_visit_id = uuid.uuid4()
    m.inventory_item_id = None
    m.inventory_item = None
    m.description = "Cable 2.5mm²"
    m.estimated_qty = Decimal("10")
    m.unit = "m"
    m.unit_cost = Decimal("1.50")
    m.created_at = _now()
    for k, val in kwargs.items():
        setattr(m, k, val)
    return m


def make_photo(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.site_visit_id = uuid.uuid4()
    p.file_path = "/uploads/site_visits/x/photos/photo.jpg"
    p.file_size_bytes = 2048
    p.caption = None
    p.sort_order = 0
    p.created_at = _now()
    for k, val in kwargs.items():
        setattr(p, k, val)
    return p


def make_doc(**kwargs) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.site_visit_id = uuid.uuid4()
    d.name = "plano.pdf"
    d.file_path = "/uploads/site_visits/x/documents/plano.pdf"
    d.file_size_bytes = 1024
    d.document_type = "other"
    d.created_at = _now()
    for k, val in kwargs.items():
        setattr(d, k, val)
    return d


def make_upload_file(
    content_type: str, filename: str, content: bytes = b"data"
) -> MagicMock:
    f = MagicMock()
    f.content_type = content_type
    f.filename = filename
    f.read = AsyncMock(return_value=content)
    return f


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


class _Mocks(NamedTuple):
    svc: SiteVisitService
    repo: AsyncMock
    material_repo: AsyncMock
    photo_repo: AsyncMock
    doc_repo: AsyncMock
    customer_repo: AsyncMock
    addr_repo: AsyncMock
    item_repo: AsyncMock
    budget_repo: AsyncMock


@pytest.fixture
def mocks(mock_session) -> _Mocks:
    """
    Patches all seven repositories injected by SiteVisitService.__init__ plus
    BudgetRepository (lazily imported inside get_visit).
    Returns a typed NamedTuple so tests can reference repos by name.
    """
    repo = AsyncMock()
    material_repo = AsyncMock()
    photo_repo = AsyncMock()
    doc_repo = AsyncMock()
    customer_repo = AsyncMock()
    addr_repo = AsyncMock()
    item_repo = AsyncMock()
    budget_repo = AsyncMock()
    budget_repo.count_by_visit.return_value = 0

    mock_budget_cls = MagicMock(return_value=budget_repo)

    with (
        patch("app.services.site_visit.SiteVisitRepository", return_value=repo),
        patch("app.services.site_visit.SiteVisitMaterialRepository", return_value=material_repo),
        patch("app.services.site_visit.SiteVisitPhotoRepository", return_value=photo_repo),
        patch("app.services.site_visit.SiteVisitDocumentRepository", return_value=doc_repo),
        patch("app.services.site_visit.CustomerRepository", return_value=customer_repo),
        patch("app.services.site_visit.CustomerAddressRepository", return_value=addr_repo),
        patch("app.services.site_visit.InventoryItemRepository", return_value=item_repo),
        patch("app.repositories.budget.BudgetRepository", mock_budget_cls),
    ):
        svc = SiteVisitService(mock_session, TENANT_ID)
        yield _Mocks(svc, repo, material_repo, photo_repo, doc_repo,
                     customer_repo, addr_repo, item_repo, budget_repo)


# ── list_visits ────────────────────────────────────────────────────────────────

class TestListVisits:
    async def test_returns_paginated_response(self, mocks):
        mocks.repo.search.return_value = ([make_visit(), make_visit()], 2)

        result = await mocks.svc.list_visits(skip=0, limit=10)

        assert result.total == 2
        assert len(result.items) == 2

    async def test_passes_all_filters_to_repo(self, mocks):
        mocks.repo.search.return_value = ([], 0)
        date_from = datetime(2024, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2024, 12, 31, tzinfo=timezone.utc)
        customer_id = uuid.uuid4()

        await mocks.svc.list_visits(
            q="juan",
            customer_id=customer_id,
            status="scheduled",
            date_from=date_from,
            date_to=date_to,
            skip=10,
            limit=20,
        )

        mocks.repo.search.assert_called_once_with(
            query="juan",
            customer_id=customer_id,
            status="scheduled",
            date_from=date_from,
            date_to=date_to,
            skip=10,
            limit=20,
        )

    async def test_empty_result(self, mocks):
        mocks.repo.search.return_value = ([], 0)

        result = await mocks.svc.list_visits()

        assert result.total == 0
        assert result.items == []

    async def test_summary_uses_address_text(self, mocks):
        visit = make_visit(address_text="Avenida Sur 10, Sevilla")
        mocks.repo.search.return_value = ([visit], 1)

        result = await mocks.svc.list_visits()

        assert result.items[0].address_display == "Avenida Sur 10, Sevilla"

    async def test_summary_fallback_address_when_none(self, mocks):
        visit = make_visit(address_text=None)
        mocks.repo.search.return_value = ([visit], 1)

        result = await mocks.svc.list_visits()

        assert result.items[0].address_display == "Sin dirección especificada"


# ── get_visit ──────────────────────────────────────────────────────────────────

class TestGetVisit:
    async def test_returns_full_response(self, mocks):
        visit = make_visit()
        mocks.repo.get_with_full_detail.return_value = visit

        result = await mocks.svc.get_visit(visit.id)

        assert result.id == visit.id

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_visit(uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert "Visita" in exc_info.value.detail

    async def test_includes_budget_count(self, mocks):
        mocks.repo.get_with_full_detail.return_value = make_visit()
        mocks.budget_repo.count_by_visit.return_value = 3

        result = await mocks.svc.get_visit(uuid.uuid4())

        assert result.budgets_count == 3

    async def test_includes_customer_name_when_linked(self, mocks):
        customer = make_customer_mock(name="Empresa SL")
        visit = make_visit(customer=customer, customer_id=customer.id)
        mocks.repo.get_with_full_detail.return_value = visit

        result = await mocks.svc.get_visit(visit.id)

        assert result.customer_name == "Empresa SL"


# ── create_visit ───────────────────────────────────────────────────────────────

class TestCreateVisit:
    def _setup_create(self, mocks, visit: MagicMock) -> None:
        """Prepares repo mocks for a successful create + get_visit call."""
        mocks.repo.create.return_value = visit
        mocks.repo.get_with_full_detail.return_value = visit

    async def test_creates_anonymous_visit(self, mocks):
        visit = make_visit()
        self._setup_create(mocks, visit)

        data = SiteVisitCreate(
            contact_name="Propietario",
            address_text="Calle 1, Madrid",
            visit_date=datetime(2024, 7, 1, tzinfo=timezone.utc),
        )
        result = await mocks.svc.create_visit(data)

        mocks.repo.create.assert_called_once()
        assert result.id == visit.id

    async def test_validates_customer_exists_when_provided(self, mocks):
        mocks.customer_repo.get_by_id.return_value = None

        data = SiteVisitCreate(
            customer_id=uuid.uuid4(),
            address_text="Calle 1, Madrid",
            visit_date=_now(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_visit(data)

        assert exc_info.value.status_code == 404
        assert "Cliente" in exc_info.value.detail

    async def test_validates_customer_address_exists_when_provided(self, mocks):
        mocks.customer_repo.get_by_id.return_value = make_customer_mock()
        mocks.addr_repo.get_by_id.return_value = None

        customer_id = uuid.uuid4()
        data = SiteVisitCreate(
            customer_id=customer_id,
            customer_address_id=uuid.uuid4(),
            visit_date=_now(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_visit(data)

        assert exc_info.value.status_code == 404
        assert "Dirección" in exc_info.value.detail

    async def test_raises_400_when_address_belongs_to_other_customer(self, mocks):
        customer_id = uuid.uuid4()
        address = make_address_mock(customer_id=uuid.uuid4())  # different customer
        mocks.customer_repo.get_by_id.return_value = make_customer_mock(id=customer_id)
        mocks.addr_repo.get_by_id.return_value = address

        data = SiteVisitCreate(
            customer_id=customer_id,
            customer_address_id=address.id,
            visit_date=_now(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_visit(data)

        assert exc_info.value.status_code == 400
        assert "pertenece" in exc_info.value.detail

    async def test_snapshots_address_text_from_customer_address(self, mocks):
        """
        When customer_address_id is provided and address_text is absent,
        the service must build a snapshot string and store it on the visit.
        """
        customer_id = uuid.uuid4()
        address = make_address_mock(
            customer_id=customer_id,
            street="Gran Vía 5",
            city="Madrid",
            postal_code="28013",
            province="Madrid",
        )
        mocks.customer_repo.get_by_id.return_value = make_customer_mock(id=customer_id)
        mocks.addr_repo.get_by_id.return_value = address
        visit = make_visit()
        self._setup_create(mocks, visit)

        data = SiteVisitCreate(
            customer_id=customer_id,
            customer_address_id=address.id,
            visit_date=_now(),
        )
        await mocks.svc.create_visit(data)

        created_visit = mocks.repo.create.call_args[0][0]
        assert "Gran Vía 5" in created_visit.address_text
        assert "Madrid" in created_visit.address_text

    async def test_explicit_address_text_not_overwritten_by_snapshot(self, mocks):
        """
        If address_text is already provided alongside customer_address_id,
        the explicit text must be preserved — no snapshot override.
        """
        customer_id = uuid.uuid4()
        address = make_address_mock(customer_id=customer_id)
        mocks.customer_repo.get_by_id.return_value = make_customer_mock(id=customer_id)
        mocks.addr_repo.get_by_id.return_value = address
        visit = make_visit()
        self._setup_create(mocks, visit)

        data = SiteVisitCreate(
            customer_id=customer_id,
            customer_address_id=address.id,
            address_text="Texto libre prioritario",
            visit_date=_now(),
        )
        await mocks.svc.create_visit(data)

        created_visit = mocks.repo.create.call_args[0][0]
        assert created_visit.address_text == "Texto libre prioritario"

    async def test_commits_session(self, mocks, mock_session):
        visit = make_visit()
        self._setup_create(mocks, visit)

        data = SiteVisitCreate(
            contact_name="Juan", address_text="Calle 1", visit_date=_now()
        )
        await mocks.svc.create_visit(data)

        mock_session.commit.assert_called_once()


# ── update_visit ───────────────────────────────────────────────────────────────

class TestUpdateVisit:
    async def test_updates_provided_fields(self, mocks):
        visit = make_visit()
        updated = make_visit(id=visit.id, description="Nueva descripción")
        mocks.repo.get_by_id.return_value = visit
        mocks.repo.get_with_full_detail.return_value = updated

        result = await mocks.svc.update_visit(
            visit.id, SiteVisitUpdate(description="Nueva descripción")
        )

        mocks.repo.update.assert_called_once_with(
            visit, {"description": "Nueva descripción"}
        )

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_visit(uuid.uuid4(), SiteVisitUpdate(description="X"))

        assert exc_info.value.status_code == 404

    @pytest.mark.parametrize("terminal_status", [
        SiteVisitStatus.COMPLETED,
        SiteVisitStatus.CANCELLED,
        SiteVisitStatus.NO_SHOW,
    ])
    async def test_raises_400_for_terminal_statuses(self, mocks, terminal_status):
        visit = make_visit(status=terminal_status)
        mocks.repo.get_by_id.return_value = visit

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_visit(visit.id, SiteVisitUpdate(description="X"))

        assert exc_info.value.status_code == 400
        assert terminal_status.value in exc_info.value.detail

    @pytest.mark.parametrize("editable_status", [
        SiteVisitStatus.SCHEDULED,
        SiteVisitStatus.IN_PROGRESS,
    ])
    async def test_allows_update_for_non_terminal_statuses(self, mocks, editable_status):
        visit = make_visit(status=editable_status)
        mocks.repo.get_by_id.return_value = visit
        mocks.repo.get_with_full_detail.return_value = visit

        await mocks.svc.update_visit(visit.id, SiteVisitUpdate(description="Edición ok"))

        mocks.repo.update.assert_called_once()

    async def test_commits_session(self, mocks, mock_session):
        visit = make_visit(status=SiteVisitStatus.SCHEDULED)
        mocks.repo.get_by_id.return_value = visit
        mocks.repo.get_with_full_detail.return_value = visit

        await mocks.svc.update_visit(visit.id, SiteVisitUpdate(description="ok"))

        mock_session.commit.assert_called_once()


# ── Status state machine ───────────────────────────────────────────────────────

class TestValidateStatusTransition:
    """Tests for the sync _validate_status_transition helper."""

    @pytest.mark.parametrize("current,new", [
        ("scheduled",   "in_progress"),
        ("scheduled",   "cancelled"),
        ("scheduled",   "no_show"),
        ("in_progress", "completed"),
        ("in_progress", "cancelled"),
        ("no_show",     "scheduled"),
    ])
    def test_valid_transitions(self, mocks, current, new):
        mocks.svc._validate_status_transition(current, new)  # must not raise

    @pytest.mark.parametrize("current,new", [
        ("scheduled",   "completed"),
        ("in_progress", "scheduled"),
        ("in_progress", "no_show"),
        ("completed",   "scheduled"),
        ("completed",   "in_progress"),
        ("cancelled",   "scheduled"),
        ("cancelled",   "in_progress"),
        ("no_show",     "in_progress"),
        ("no_show",     "completed"),
    ])
    def test_invalid_transitions_raise_400(self, mocks, current, new):
        with pytest.raises(HTTPException) as exc_info:
            mocks.svc._validate_status_transition(current, new)

        assert exc_info.value.status_code == 400
        assert current in exc_info.value.detail
        assert new in exc_info.value.detail

    def test_transition_map_covers_all_statuses(self):
        """Every SiteVisitStatus value must appear as a key in _VALID_TRANSITIONS."""
        all_values = {s.value for s in SiteVisitStatus}
        assert set(_VALID_TRANSITIONS.keys()) == all_values


class TestUpdateStatus:
    async def test_applies_valid_transition(self, mocks):
        visit = make_visit(status=SiteVisitStatus.SCHEDULED)
        mocks.repo.get_by_id.return_value = visit
        mocks.repo.get_with_full_detail.return_value = make_visit(
            id=visit.id, status=SiteVisitStatus.IN_PROGRESS
        )

        await mocks.svc.update_status(
            visit.id, SiteVisitStatusUpdate(status="in_progress")
        )

        mocks.repo.update.assert_called_once_with(visit, {"status": "in_progress"})

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_status(uuid.uuid4(), SiteVisitStatusUpdate(status="completed"))

        assert exc_info.value.status_code == 404

    async def test_raises_400_on_invalid_transition(self, mocks):
        visit = make_visit(status=SiteVisitStatus.COMPLETED)
        mocks.repo.get_by_id.return_value = visit

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_status(
                visit.id, SiteVisitStatusUpdate(status="scheduled")
            )

        assert exc_info.value.status_code == 400

    async def test_commits_session(self, mocks, mock_session):
        visit = make_visit(status=SiteVisitStatus.SCHEDULED)
        mocks.repo.get_by_id.return_value = visit
        mocks.repo.get_with_full_detail.return_value = visit

        await mocks.svc.update_status(visit.id, SiteVisitStatusUpdate(status="in_progress"))

        mock_session.commit.assert_called_once()


# ── link_customer ──────────────────────────────────────────────────────────────

class TestLinkCustomer:
    async def test_links_customer_successfully(self, mocks):
        visit = make_visit(customer_id=None)
        customer_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = visit
        mocks.customer_repo.get_by_id.return_value = make_customer_mock(id=customer_id)
        mocks.repo.get_with_full_detail.return_value = make_visit(customer_id=customer_id)

        await mocks.svc.link_customer(
            visit.id, SiteVisitLinkCustomer(customer_id=customer_id)
        )

        mocks.repo.update.assert_called_once()
        update_data = mocks.repo.update.call_args[0][1]
        assert update_data["customer_id"] == customer_id

    async def test_also_links_address_when_provided(self, mocks):
        visit = make_visit(customer_id=None)
        customer_id = uuid.uuid4()
        address_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = visit
        mocks.customer_repo.get_by_id.return_value = make_customer_mock(id=customer_id)
        mocks.repo.get_with_full_detail.return_value = visit

        await mocks.svc.link_customer(
            visit.id,
            SiteVisitLinkCustomer(customer_id=customer_id, customer_address_id=address_id),
        )

        update_data = mocks.repo.update.call_args[0][1]
        assert update_data["customer_address_id"] == address_id

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.link_customer(
                uuid.uuid4(), SiteVisitLinkCustomer(customer_id=uuid.uuid4())
            )

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_visit_already_has_customer(self, mocks):
        visit = make_visit(customer_id=uuid.uuid4())  # already linked
        mocks.repo.get_by_id.return_value = visit

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.link_customer(
                visit.id, SiteVisitLinkCustomer(customer_id=uuid.uuid4())
            )

        assert exc_info.value.status_code == 400
        assert "ya tiene un cliente" in exc_info.value.detail

    async def test_raises_404_when_customer_not_found(self, mocks):
        visit = make_visit(customer_id=None)
        mocks.repo.get_by_id.return_value = visit
        mocks.customer_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.link_customer(
                visit.id, SiteVisitLinkCustomer(customer_id=uuid.uuid4())
            )

        assert exc_info.value.status_code == 404
        assert "Cliente" in exc_info.value.detail


# ── Materials ──────────────────────────────────────────────────────────────────

class TestListMaterials:
    async def test_returns_materials(self, mocks):
        visit = make_visit(materials=[make_material(), make_material()])
        mocks.repo.get_with_full_detail.return_value = visit

        result = await mocks.svc.list_materials(visit.id)

        assert len(result) == 2

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.list_materials(uuid.uuid4())

        assert exc_info.value.status_code == 404


class TestAddMaterial:
    async def test_adds_free_text_material(self, mocks):
        visit_id = uuid.uuid4()
        material = make_material(site_visit_id=visit_id)
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.material_repo.create.return_value = material

        result = await mocks.svc.add_material(
            visit_id,
            SiteVisitMaterialCreate(description="Cable 2.5mm²", estimated_qty=Decimal("10")),
        )

        mocks.material_repo.create.assert_called_once()
        assert result.description == material.description

    async def test_inherits_unit_and_cost_from_inventory_item(self, mocks):
        visit_id = uuid.uuid4()
        item = MagicMock()
        item.id = uuid.uuid4()  # must be a real UUID — Pydantic rejects MagicMock
        item.name = "Cable NYM"
        item.unit = "m"
        item.unit_cost_avg = Decimal("2.00")
        item.unit_cost = Decimal("1.80")

        material = make_material(
            site_visit_id=visit_id,
            inventory_item_id=item.id,
            unit="m",
            unit_cost=Decimal("2.00"),
        )
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.item_repo.get_by_id.return_value = item
        mocks.material_repo.create.return_value = material

        result = await mocks.svc.add_material(
            visit_id,
            SiteVisitMaterialCreate(inventory_item_id=item.id, estimated_qty=Decimal("5")),
        )

        assert result.inventory_item_name == "Cable NYM"
        assert result.unit == "m"

    async def test_explicit_unit_not_overwritten_by_item(self, mocks):
        """Unit provided by the caller must take precedence over the inventory item's."""
        visit_id = uuid.uuid4()
        item = MagicMock()
        item.id = uuid.uuid4()  # must be a real UUID — Pydantic rejects MagicMock
        item.name = "Cable"
        item.unit = "m"
        item.unit_cost_avg = None
        item.unit_cost = Decimal("1.00")

        material = make_material(site_visit_id=visit_id, unit="ud")
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.item_repo.get_by_id.return_value = item
        mocks.material_repo.create.return_value = material

        await mocks.svc.add_material(
            visit_id,
            SiteVisitMaterialCreate(
                inventory_item_id=item.id, estimated_qty=Decimal("3"), unit="ud"
            ),
        )

        created = mocks.material_repo.create.call_args[0][0]
        assert created.unit == "ud"

    async def test_raises_404_when_inventory_item_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = make_visit()
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_material(
                uuid.uuid4(),
                SiteVisitMaterialCreate(
                    inventory_item_id=uuid.uuid4(), estimated_qty=Decimal("1")
                ),
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_material(
                uuid.uuid4(),
                SiteVisitMaterialCreate(description="Cable", estimated_qty=Decimal("1")),
            )

        assert exc_info.value.status_code == 404

    async def test_calculates_subtotal_when_unit_cost_present(self, mocks):
        visit_id = uuid.uuid4()
        material = make_material(
            site_visit_id=visit_id,
            estimated_qty=Decimal("10"),
            unit_cost=Decimal("2.50"),
        )
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.material_repo.create.return_value = material

        result = await mocks.svc.add_material(
            visit_id,
            SiteVisitMaterialCreate(description="Cable", estimated_qty=Decimal("10")),
        )

        assert result.subtotal == Decimal("25.00")

    async def test_subtotal_is_none_when_no_unit_cost(self, mocks):
        visit_id = uuid.uuid4()
        material = make_material(site_visit_id=visit_id, unit_cost=None)
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.material_repo.create.return_value = material

        result = await mocks.svc.add_material(
            visit_id,
            SiteVisitMaterialCreate(description="Cable", estimated_qty=Decimal("5")),
        )

        assert result.subtotal is None

    async def test_commits_session(self, mocks, mock_session):
        material = make_material()
        mocks.repo.get_by_id.return_value = make_visit()
        mocks.material_repo.create.return_value = material

        await mocks.svc.add_material(
            uuid.uuid4(),
            SiteVisitMaterialCreate(description="Cable", estimated_qty=Decimal("1")),
        )

        mock_session.commit.assert_called_once()


class TestUpdateMaterial:
    async def test_updates_fields(self, mocks):
        visit_id = uuid.uuid4()
        material = make_material(site_visit_id=visit_id)
        mocks.material_repo.get_by_id.return_value = material

        await mocks.svc.update_material(
            visit_id, material.id, SiteVisitMaterialUpdate(unit="ud")
        )

        mocks.material_repo.update.assert_called_once_with(material, {"unit": "ud"})

    async def test_raises_404_when_not_found(self, mocks):
        mocks.material_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_material(
                uuid.uuid4(), uuid.uuid4(), SiteVisitMaterialUpdate(unit="m")
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_visit(self, mocks):
        material = make_material(site_visit_id=uuid.uuid4())
        mocks.material_repo.get_by_id.return_value = material

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_material(
                uuid.uuid4(), material.id, SiteVisitMaterialUpdate(unit="m")
            )

        assert exc_info.value.status_code == 404


class TestDeleteMaterial:
    async def test_deletes_material(self, mocks):
        visit_id = uuid.uuid4()
        material = make_material(site_visit_id=visit_id)
        mocks.material_repo.get_by_id.return_value = material

        await mocks.svc.delete_material(visit_id, material.id)

        mocks.material_repo.delete.assert_called_once_with(material)

    async def test_raises_404_when_not_found(self, mocks):
        mocks.material_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_material(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_visit(self, mocks):
        material = make_material(site_visit_id=uuid.uuid4())
        mocks.material_repo.get_by_id.return_value = material

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_material(uuid.uuid4(), material.id)

        assert exc_info.value.status_code == 404


# ── Photos ─────────────────────────────────────────────────────────────────────

class TestListPhotos:
    async def test_returns_photos(self, mocks):
        visit_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.photo_repo.get_by_visit.return_value = [make_photo(), make_photo()]

        result = await mocks.svc.list_photos(visit_id)

        assert len(result) == 2

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.list_photos(uuid.uuid4())

        assert exc_info.value.status_code == 404


class TestUploadPhoto:
    async def test_raises_400_on_non_image_content_type(self, mocks):
        mocks.repo.get_by_id.return_value = make_visit()
        file = make_upload_file("application/pdf", "doc.pdf")

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_photo(uuid.uuid4(), file, None)

        assert exc_info.value.status_code == 400
        assert "imagen" in exc_info.value.detail

    async def test_raises_400_when_content_type_is_none(self, mocks):
        mocks.repo.get_by_id.return_value = make_visit()
        file = make_upload_file(None, "photo.jpg")

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_photo(uuid.uuid4(), file, None)

        assert exc_info.value.status_code == 400

    async def test_raises_413_when_file_too_large(self, mocks):
        mocks.repo.get_by_id.return_value = make_visit()
        large_content = b"x" * (11 * 1024 * 1024)
        file = make_upload_file("image/jpeg", "photo.jpg", large_content)

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_photo(uuid.uuid4(), file, None)

        assert exc_info.value.status_code == 413

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None
        file = make_upload_file("image/jpeg", "photo.jpg")

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_photo(uuid.uuid4(), file, None)

        assert exc_info.value.status_code == 404

    async def test_saves_file_and_creates_photo(self, mocks, tmp_path):
        visit_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        photo = make_photo(site_visit_id=visit_id)
        mocks.photo_repo.create.return_value = photo
        mocks.photo_repo.get_by_visit.return_value = []  # no existing photos
        file = make_upload_file("image/jpeg", "foto.jpg", b"image data")

        with patch("app.services.site_visit.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await mocks.svc.upload_photo(visit_id, file, "Vista frontal")

        mocks.photo_repo.create.assert_called_once()

    async def test_sort_order_is_next_available(self, mocks, tmp_path):
        """Sort order for a new photo must equal the count of existing photos."""
        visit_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        photo = make_photo(site_visit_id=visit_id, sort_order=2)
        mocks.photo_repo.create.return_value = photo
        mocks.photo_repo.get_by_visit.return_value = [make_photo(), make_photo()]  # 2 existing
        file = make_upload_file("image/png", "nueva.png", b"img")

        with patch("app.services.site_visit.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await mocks.svc.upload_photo(visit_id, file, None)

        created = mocks.photo_repo.create.call_args[0][0]
        assert created.sort_order == 2

    @pytest.mark.parametrize("mime", ["image/jpeg", "image/png", "image/webp"])
    async def test_accepts_standard_image_types(self, mocks, tmp_path, mime):
        mocks.repo.get_by_id.return_value = make_visit()
        mocks.photo_repo.create.return_value = make_photo()
        mocks.photo_repo.get_by_visit.return_value = []
        file = make_upload_file(mime, "photo.jpg", b"img")

        with patch("app.services.site_visit.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await mocks.svc.upload_photo(uuid.uuid4(), file, None)  # must not raise


class TestUpdatePhoto:
    async def test_updates_caption(self, mocks):
        visit_id = uuid.uuid4()
        photo = make_photo(site_visit_id=visit_id)
        mocks.photo_repo.get_by_id.return_value = photo

        await mocks.svc.update_photo(visit_id, photo.id, SiteVisitPhotoUpdate(caption="Cuadro"))

        mocks.photo_repo.update.assert_called_once_with(photo, {"caption": "Cuadro"})

    async def test_raises_404_when_not_found(self, mocks):
        mocks.photo_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_photo(
                uuid.uuid4(), uuid.uuid4(), SiteVisitPhotoUpdate(caption="X")
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_visit(self, mocks):
        photo = make_photo(site_visit_id=uuid.uuid4())
        mocks.photo_repo.get_by_id.return_value = photo

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_photo(
                uuid.uuid4(), photo.id, SiteVisitPhotoUpdate(caption="X")
            )

        assert exc_info.value.status_code == 404


class TestDeletePhoto:
    async def test_deletes_photo_and_physical_file(self, mocks, tmp_path):
        visit_id = uuid.uuid4()
        temp_file = tmp_path / "photo.jpg"
        temp_file.write_bytes(b"img")
        photo = make_photo(site_visit_id=visit_id, file_path=str(temp_file))
        mocks.photo_repo.get_by_id.return_value = photo

        await mocks.svc.delete_photo(visit_id, photo.id)

        mocks.photo_repo.delete.assert_called_once_with(photo)
        assert not temp_file.exists()

    async def test_deletes_photo_when_file_missing(self, mocks):
        visit_id = uuid.uuid4()
        photo = make_photo(site_visit_id=visit_id, file_path="/nonexistent/photo.jpg")
        mocks.photo_repo.get_by_id.return_value = photo

        await mocks.svc.delete_photo(visit_id, photo.id)  # must not raise

        mocks.photo_repo.delete.assert_called_once_with(photo)

    async def test_raises_404_when_not_found(self, mocks):
        mocks.photo_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_photo(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_visit(self, mocks):
        photo = make_photo(site_visit_id=uuid.uuid4())
        mocks.photo_repo.get_by_id.return_value = photo

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_photo(uuid.uuid4(), photo.id)

        assert exc_info.value.status_code == 404


class TestReorderPhotos:
    async def test_delegates_to_repo_and_returns_ordered_list(self, mocks):
        visit_id = uuid.uuid4()
        photo_ids = [uuid.uuid4(), uuid.uuid4()]
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.photo_repo.get_by_visit.return_value = [
            make_photo(id=photo_ids[0], sort_order=0),
            make_photo(id=photo_ids[1], sort_order=1),
        ]

        result = await mocks.svc.reorder_photos(visit_id, photo_ids)

        mocks.repo.reorder_photos.assert_called_once_with(visit_id, photo_ids)
        assert len(result) == 2

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reorder_photos(uuid.uuid4(), [uuid.uuid4()])

        assert exc_info.value.status_code == 404


# ── Documents ──────────────────────────────────────────────────────────────────

class TestListDocuments:
    async def test_returns_documents(self, mocks):
        visit = make_visit(documents=[make_doc(), make_doc()])
        mocks.repo.get_with_full_detail.return_value = visit

        result = await mocks.svc.list_documents(visit.id)

        assert len(result) == 2

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.list_documents(uuid.uuid4())

        assert exc_info.value.status_code == 404


class TestUploadDocument:
    async def test_raises_413_when_file_too_large(self, mocks):
        mocks.repo.get_by_id.return_value = make_visit()
        large_content = b"x" * (11 * 1024 * 1024)
        file = make_upload_file("application/pdf", "plano.pdf", large_content)

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_document(uuid.uuid4(), file, "other", None)

        assert exc_info.value.status_code == 413

    async def test_raises_404_when_visit_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None
        file = make_upload_file("application/pdf", "doc.pdf")

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.upload_document(uuid.uuid4(), file, "other", None)

        assert exc_info.value.status_code == 404

    async def test_saves_file_and_creates_document(self, mocks, tmp_path):
        visit_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        doc = make_doc(site_visit_id=visit_id)
        mocks.doc_repo.create.return_value = doc
        file = make_upload_file("application/pdf", "plano.pdf", b"pdf content")

        with patch("app.services.site_visit.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await mocks.svc.upload_document(visit_id, file, "other", "Plano eléctrico")

        mocks.doc_repo.create.assert_called_once()

    async def test_uses_filename_as_name_when_none_given(self, mocks, tmp_path):
        visit_id = uuid.uuid4()
        mocks.repo.get_by_id.return_value = make_visit(id=visit_id)
        mocks.doc_repo.create.return_value = make_doc(site_visit_id=visit_id)
        file = make_upload_file("application/pdf", "esquema.pdf", b"data")

        with patch("app.services.site_visit.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await mocks.svc.upload_document(visit_id, file, "other", None)

        created = mocks.doc_repo.create.call_args[0][0]
        assert created.name == "esquema.pdf"


class TestDeleteDocument:
    async def test_deletes_document_and_physical_file(self, mocks, tmp_path):
        visit_id = uuid.uuid4()
        temp_file = tmp_path / "doc.pdf"
        temp_file.write_bytes(b"pdf")
        doc = make_doc(site_visit_id=visit_id, file_path=str(temp_file))
        mocks.doc_repo.get_by_id.return_value = doc

        await mocks.svc.delete_document(visit_id, doc.id)

        mocks.doc_repo.delete.assert_called_once_with(doc)
        assert not temp_file.exists()

    async def test_deletes_document_when_file_missing(self, mocks):
        visit_id = uuid.uuid4()
        doc = make_doc(site_visit_id=visit_id, file_path="/nonexistent/doc.pdf")
        mocks.doc_repo.get_by_id.return_value = doc

        await mocks.svc.delete_document(visit_id, doc.id)  # must not raise

        mocks.doc_repo.delete.assert_called_once_with(doc)

    async def test_raises_404_when_not_found(self, mocks):
        mocks.doc_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_document(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_visit(self, mocks):
        doc = make_doc(site_visit_id=uuid.uuid4())
        mocks.doc_repo.get_by_id.return_value = doc

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_document(uuid.uuid4(), doc.id)

        assert exc_info.value.status_code == 404


# ── Private helpers ────────────────────────────────────────────────────────────

class TestResolveAddress:
    def test_returns_address_text_when_present(self, mocks):
        visit = make_visit(address_text="Calle Mayor 1, Madrid")
        assert mocks.svc._resolve_address(visit) == "Calle Mayor 1, Madrid"

    def test_fallback_when_no_address_text(self, mocks):
        visit = make_visit(address_text=None)
        assert mocks.svc._resolve_address(visit) == "Sin dirección especificada"


class TestBuildSummary:
    def test_summary_without_customer(self, mocks):
        visit = make_visit(customer=None, customer_id=None)
        summary = mocks.svc._build_summary(visit)

        assert summary.customer_id is None
        assert summary.customer_name is None
        assert summary.customer_type is None

    def test_summary_with_customer(self, mocks):
        customer = make_customer_mock(name="Juan García")
        visit = make_visit(customer=customer, customer_id=customer.id)
        summary = mocks.svc._build_summary(visit)

        assert summary.customer_name == "Juan García"
        assert summary.customer_type == "individual"

    def test_has_photos_flag(self, mocks):
        visit_with = make_visit(photos=[make_photo()])
        visit_without = make_visit(photos=[])

        assert mocks.svc._build_summary(visit_with).has_photos is True
        assert mocks.svc._build_summary(visit_without).has_photos is False

    def test_has_documents_flag(self, mocks):
        visit_with = make_visit(documents=[make_doc()])
        visit_without = make_visit(documents=[])

        assert mocks.svc._build_summary(visit_with).has_documents is True
        assert mocks.svc._build_summary(visit_without).has_documents is False

    def test_materials_count(self, mocks):
        visit = make_visit(materials=[make_material(), make_material(), make_material()])
        summary = mocks.svc._build_summary(visit)
        assert summary.materials_count == 3


class TestBuildMaterialResponse:
    def test_response_without_inventory_item(self, mocks):
        material = make_material(
            inventory_item=None,
            inventory_item_id=None,
            description="Cable libre",
            estimated_qty=Decimal("5"),
            unit_cost=Decimal("2.00"),
        )
        result = mocks.svc._build_material_response(material)

        assert result.inventory_item_name is None
        assert result.description == "Cable libre"
        assert result.subtotal == Decimal("10.00")

    def test_response_with_inventory_item_name(self, mocks):
        item = MagicMock()
        item.name = "Interruptor diferencial"
        material = make_material(
            inventory_item=item,
            estimated_qty=Decimal("2"),
            unit_cost=Decimal("45.00"),
        )
        result = mocks.svc._build_material_response(material)

        assert result.inventory_item_name == "Interruptor diferencial"
        assert result.subtotal == Decimal("90.00")

    def test_subtotal_is_none_when_no_unit_cost(self, mocks):
        material = make_material(unit_cost=None, inventory_item=None)
        result = mocks.svc._build_material_response(material)
        assert result.subtotal is None
