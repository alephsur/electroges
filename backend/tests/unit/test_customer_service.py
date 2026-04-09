"""
Unit tests for CustomerService.

Repositories and session are mocked so no database is needed.
All service methods are tested in isolation: business logic, error handling,
delegation to repositories, and commit behaviour.
"""
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.customer import CustomerType
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerUpdate,
)
from app.services.customer import CustomerService

TENANT_ID = uuid.uuid4()


# ── Test-object factories ──────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_customer(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a Customer model instance."""
    c = MagicMock()
    c.id = uuid.uuid4()
    c.tenant_id = TENANT_ID
    c.name = "Juan García"
    c.customer_type = CustomerType.INDIVIDUAL
    c.tax_id = None
    c.email = "juan@example.com"
    c.phone = "600000001"
    c.phone_secondary = None
    c.contact_person = None
    c.notes = None
    c.is_active = True
    c.addresses = []
    c.documents = []
    c.created_at = _now()
    c.updated_at = _now()
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def make_address(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a CustomerAddress model instance."""
    a = MagicMock()
    a.id = uuid.uuid4()
    a.customer_id = uuid.uuid4()
    a.address_type = "service"
    a.label = None
    a.street = "Calle Mayor 1"
    a.city = "Madrid"
    a.postal_code = "28001"
    a.province = None
    a.is_default = False
    a.created_at = _now()
    a.updated_at = _now()
    for k, v in kwargs.items():
        setattr(a, k, v)
    return a


def make_document(**kwargs) -> MagicMock:
    """Return a MagicMock that quacks like a CustomerDocument model instance."""
    d = MagicMock()
    d.id = uuid.uuid4()
    d.customer_id = uuid.uuid4()
    d.name = "contrato.pdf"
    d.file_path = "/uploads/customers/x/contrato.pdf"
    d.file_size_bytes = 1024
    d.document_type = "contract"
    d.created_at = _now()
    d.updated_at = _now()
    for k, v in kwargs.items():
        setattr(d, k, v)
    return d


def make_timeline_event(event_date: datetime, **kwargs) -> "TimelineEvent":
    """Return a real TimelineEvent instance (Pydantic rejects MagicMocks)."""
    from app.schemas.customer import TimelineEvent

    defaults = dict(
        event_type="site_visit",
        event_date=event_date,
        title="Evento de prueba",
        subtitle=None,
        reference_id=uuid.uuid4(),
        reference_type="site_visit",
    )
    defaults.update(kwargs)
    return TimelineEvent(**defaults)


def make_upload_file(
    content_type: str,
    filename: str,
    content: bytes = b"fake content",
) -> MagicMock:
    """Return a MagicMock that quacks like a FastAPI UploadFile."""
    f = MagicMock()
    f.content_type = content_type
    f.filename = filename
    f.read = AsyncMock(return_value=content)
    return f


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()  # sync method on AsyncSession
    return session


@pytest.fixture
def service_with_mocks(mock_session):
    """
    Yields (service, mock_repo, mock_addr_repo, mock_doc_repo).

    All three repository classes are patched so CustomerService uses our mocks
    instead of real repositories that would need a database session.
    """
    mock_repo = AsyncMock()
    mock_addr_repo = AsyncMock()
    mock_doc_repo = AsyncMock()

    with (
        patch("app.services.customer.CustomerRepository", return_value=mock_repo),
        patch("app.services.customer.CustomerAddressRepository", return_value=mock_addr_repo),
        patch("app.services.customer.CustomerDocumentRepository", return_value=mock_doc_repo),
    ):
        svc = CustomerService(mock_session, TENANT_ID)
        yield svc, mock_repo, mock_addr_repo, mock_doc_repo


# ── list_customers ─────────────────────────────────────────────────────────────

class TestListCustomers:
    async def test_returns_paginated_response(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.search.return_value = ([make_customer(), make_customer()], 2)

        result = await svc.list_customers(skip=0, limit=10)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 10

    async def test_passes_all_filters_to_repo(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.search.return_value = ([], 0)

        await svc.list_customers(
            q="juan", customer_type="individual", is_active=True, skip=5, limit=20
        )

        repo.search.assert_called_once_with(
            query="juan",
            customer_type="individual",
            is_active=True,
            skip=5,
            limit=20,
        )

    async def test_empty_result(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.search.return_value = ([], 0)

        result = await svc.list_customers()

        assert result.total == 0
        assert result.items == []

    async def test_builds_one_summary_per_customer(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.search.return_value = ([make_customer(), make_customer(), make_customer()], 3)

        result = await svc.list_customers()

        assert len(result.items) == 3


# ── get_customer ───────────────────────────────────────────────────────────────

class TestGetCustomer:
    async def test_returns_full_response_when_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer = make_customer(name="Ana Martínez")
        repo.get_with_detail.return_value = customer

        result = await svc.get_customer(customer.id)

        assert result.id == customer.id
        assert result.name == "Ana Martínez"

    async def test_raises_404_when_not_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_with_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_customer(uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert "Cliente no encontrado" in exc_info.value.detail

    async def test_includes_addresses_in_response(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        addr = make_address()
        customer = make_customer(addresses=[addr])
        repo.get_with_detail.return_value = customer

        result = await svc.get_customer(customer.id)

        assert len(result.addresses) == 1

    async def test_includes_documents_in_response(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        doc = make_document()
        customer = make_customer(documents=[doc])
        repo.get_with_detail.return_value = customer

        result = await svc.get_customer(customer.id)

        assert len(result.documents) == 1


# ── create_customer ────────────────────────────────────────────────────────────

class TestCreateCustomer:
    async def test_creates_customer_and_returns_response(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        new_customer = make_customer(name="María López")
        repo.create.return_value = new_customer
        repo.get_with_detail.return_value = new_customer

        result = await svc.create_customer(CustomerCreate(name="María López"))

        repo.create.assert_called_once()
        assert result.name == "María López"

    async def test_creates_initial_address_when_provided(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        new_customer = make_customer()
        new_addr = make_address(customer_id=new_customer.id)
        repo.create.return_value = new_customer
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [new_addr]
        repo.get_with_detail.return_value = new_customer

        data = CustomerCreate(
            name="Test",
            initial_address=CustomerAddressCreate(
                street="Gran Vía 10", city="Madrid", postal_code="28013"
            ),
        )
        await svc.create_customer(data)

        addr_repo.create.assert_called_once()

    async def test_initial_address_is_forced_to_default(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        new_customer = make_customer()
        new_addr = make_address(customer_id=new_customer.id)
        repo.create.return_value = new_customer
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [new_addr]
        repo.get_with_detail.return_value = new_customer

        data = CustomerCreate(
            name="Test",
            initial_address=CustomerAddressCreate(
                street="Calle 1", city="Madrid", postal_code="28001", is_default=False
            ),
        )
        await svc.create_customer(data)

        # The address passed to addr_repo.create should have is_default=True
        created_addr = addr_repo.create.call_args[0][0]
        assert created_addr.is_default is True

    async def test_raises_409_on_duplicate_tax_id(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_tax_id.return_value = make_customer(tax_id="12345678A")

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_customer(CustomerCreate(name="Test", tax_id="12345678A"))

        assert exc_info.value.status_code == 409
        assert "12345678A" in exc_info.value.detail

    async def test_skips_tax_id_check_when_none(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        new_customer = make_customer()
        repo.create.return_value = new_customer
        repo.get_with_detail.return_value = new_customer

        await svc.create_customer(CustomerCreate(name="Sin NIF"))

        repo.get_by_tax_id.assert_not_called()

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, *_ = service_with_mocks
        new_customer = make_customer()
        repo.create.return_value = new_customer
        repo.get_with_detail.return_value = new_customer

        await svc.create_customer(CustomerCreate(name="Test"))

        mock_session.commit.assert_called_once()


# ── update_customer ────────────────────────────────────────────────────────────

class TestUpdateCustomer:
    async def test_updates_provided_fields(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer = make_customer(name="Nombre Viejo")
        updated = make_customer(name="Nombre Nuevo", id=customer.id)
        repo.get_by_id.return_value = customer
        repo.get_with_detail.return_value = updated

        result = await svc.update_customer(customer.id, CustomerUpdate(name="Nombre Nuevo"))

        repo.update.assert_called_once_with(customer, {"name": "Nombre Nuevo"})
        assert result.name == "Nombre Nuevo"

    async def test_raises_404_when_not_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_customer(uuid.uuid4(), CustomerUpdate(name="Test"))

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_tax_id_taken_by_another(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer = make_customer(tax_id="11111111A")
        repo.get_by_id.return_value = customer
        repo.get_by_tax_id.return_value = make_customer(tax_id="22222222B")  # another customer

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_customer(customer.id, CustomerUpdate(tax_id="22222222B"))

        assert exc_info.value.status_code == 409

    async def test_allows_same_tax_id_unchanged(self, service_with_mocks):
        """
        Setting the same tax_id that the customer already has must NOT trigger
        the uniqueness check (would raise 409 on itself).
        """
        svc, repo, *_ = service_with_mocks
        customer = make_customer(tax_id="11111111A")
        repo.get_by_id.return_value = customer
        repo.get_with_detail.return_value = customer

        await svc.update_customer(customer.id, CustomerUpdate(tax_id="11111111A"))

        repo.get_by_tax_id.assert_not_called()

    async def test_only_passes_set_fields_to_repo(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer = make_customer()
        repo.get_by_id.return_value = customer
        repo.get_with_detail.return_value = customer

        await svc.update_customer(customer.id, CustomerUpdate(phone="611222333"))

        call_kwargs = repo.update.call_args[0][1]  # second positional arg = data dict
        assert "phone" in call_kwargs
        assert "name" not in call_kwargs

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, *_ = service_with_mocks
        customer = make_customer()
        repo.get_by_id.return_value = customer
        repo.get_with_detail.return_value = customer

        await svc.update_customer(customer.id, CustomerUpdate(notes="nota"))

        mock_session.commit.assert_called_once()


# ── deactivate_customer ────────────────────────────────────────────────────────

class TestDeactivateCustomer:
    async def test_sets_is_active_false(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer = make_customer(is_active=True)
        repo.get_by_id.return_value = customer

        await svc.deactivate_customer(customer.id)

        repo.update.assert_called_once_with(customer, {"is_active": False})

    async def test_raises_404_when_not_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.deactivate_customer(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()

        await svc.deactivate_customer(uuid.uuid4())

        mock_session.commit.assert_called_once()


# ── list_addresses ─────────────────────────────────────────────────────────────

class TestListAddresses:
    async def test_returns_addresses_for_existing_customer(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.get_by_customer.return_value = [make_address(), make_address()]

        result = await svc.list_addresses(customer_id)

        assert len(result) == 2

    async def test_raises_404_for_unknown_customer(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.list_addresses(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_delegates_to_addr_repo(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.get_by_customer.return_value = []

        await svc.list_addresses(customer_id)

        addr_repo.get_by_customer.assert_called_once_with(customer_id)


# ── add_address ────────────────────────────────────────────────────────────────

class TestAddAddress:
    async def test_first_address_becomes_default_automatically(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        new_addr = make_address(customer_id=customer_id)
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [new_addr]  # len == 1

        await svc.add_address(
            customer_id,
            CustomerAddressCreate(street="Calle 1", city="Madrid", postal_code="28001"),
        )

        addr_repo.set_default.assert_called_once_with(new_addr.id, customer_id)

    async def test_explicit_is_default_triggers_set_default(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        existing = make_address(customer_id=customer_id, is_default=True)
        new_addr = make_address(customer_id=customer_id, is_default=True)
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [existing, new_addr]  # len == 2

        await svc.add_address(
            customer_id,
            CustomerAddressCreate(
                street="Gran Vía 10", city="Madrid", postal_code="28013", is_default=True
            ),
        )

        addr_repo.set_default.assert_called_once_with(new_addr.id, customer_id)

    async def test_nth_address_without_default_flag_not_set_as_default(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        existing = make_address(customer_id=customer_id, is_default=True)
        new_addr = make_address(customer_id=customer_id, is_default=False)
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [existing, new_addr]  # len == 2

        await svc.add_address(
            customer_id,
            CustomerAddressCreate(
                street="Avenida Sur 3", city="Sevilla", postal_code="41001", is_default=False
            ),
        )

        addr_repo.set_default.assert_not_called()

    async def test_raises_404_for_unknown_customer(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_address(
                uuid.uuid4(),
                CustomerAddressCreate(street="Calle 1", city="Madrid", postal_code="28001"),
            )

        assert exc_info.value.status_code == 404

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        new_addr = make_address(customer_id=customer_id)
        repo.get_by_id.return_value = make_customer(id=customer_id)
        addr_repo.create.return_value = new_addr
        addr_repo.get_by_customer.return_value = [new_addr, make_address()]

        await svc.add_address(
            customer_id,
            CustomerAddressCreate(street="X", city="Y", postal_code="Z"),
        )

        mock_session.commit.assert_called_once()


# ── update_address ─────────────────────────────────────────────────────────────

class TestUpdateAddress:
    async def test_updates_provided_fields(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id, city="Madrid")
        addr_repo.get_by_id.return_value = addr

        await svc.update_address(customer_id, addr.id, CustomerAddressUpdate(city="Sevilla"))

        addr_repo.update.assert_called_once_with(addr, {"city": "Sevilla"})

    async def test_raises_404_when_address_not_found(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_address(
                uuid.uuid4(), uuid.uuid4(), CustomerAddressUpdate(city="Test")
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_address_belongs_to_other_customer(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr = make_address(customer_id=uuid.uuid4())  # different customer
        addr_repo.get_by_id.return_value = addr

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_address(
                uuid.uuid4(), addr.id, CustomerAddressUpdate(city="Test")
            )

        assert exc_info.value.status_code == 404

    async def test_is_default_true_calls_set_default(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr

        await svc.update_address(
            customer_id, addr.id, CustomerAddressUpdate(is_default=True)
        )

        addr_repo.set_default.assert_called_once_with(addr.id, customer_id)

    async def test_is_default_false_does_not_call_set_default(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr

        await svc.update_address(
            customer_id, addr.id, CustomerAddressUpdate(is_default=False, city="Murcia")
        )

        addr_repo.set_default.assert_not_called()

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr

        await svc.update_address(customer_id, addr.id, CustomerAddressUpdate(city="Test"))

        mock_session.commit.assert_called_once()


# ── delete_address ─────────────────────────────────────────────────────────────

class TestDeleteAddress:
    async def test_deletes_address_when_multiple_exist(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr
        addr_repo.get_by_customer.return_value = [addr, make_address()]

        await svc.delete_address(customer_id, addr.id)

        addr_repo.delete.assert_called_once_with(addr)

    async def test_raises_400_when_only_one_address_remains(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr
        addr_repo.get_by_customer.return_value = [addr]  # only one

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_address(customer_id, addr.id)

        assert exc_info.value.status_code == 400
        addr_repo.delete.assert_not_called()

    async def test_raises_404_when_address_not_found(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_address(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_address_belongs_to_other_customer(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr = make_address(customer_id=uuid.uuid4())
        addr_repo.get_by_id.return_value = addr

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_address(uuid.uuid4(), addr.id)

        assert exc_info.value.status_code == 404

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr
        addr_repo.get_by_customer.return_value = [addr, make_address()]

        await svc.delete_address(customer_id, addr.id)

        mock_session.commit.assert_called_once()


# ── set_default_address ────────────────────────────────────────────────────────

class TestSetDefaultAddress:
    async def test_delegates_to_repo(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr

        await svc.set_default_address(customer_id, addr.id)

        addr_repo.set_default.assert_called_once_with(addr.id, customer_id)

    async def test_raises_404_when_not_found(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.set_default_address(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_other_customer(self, service_with_mocks):
        svc, repo, addr_repo, _ = service_with_mocks
        addr = make_address(customer_id=uuid.uuid4())
        addr_repo.get_by_id.return_value = addr

        with pytest.raises(HTTPException) as exc_info:
            await svc.set_default_address(uuid.uuid4(), addr.id)

        assert exc_info.value.status_code == 404

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, addr_repo, _ = service_with_mocks
        customer_id = uuid.uuid4()
        addr = make_address(customer_id=customer_id)
        addr_repo.get_by_id.return_value = addr

        await svc.set_default_address(customer_id, addr.id)

        mock_session.commit.assert_called_once()


# ── list_documents ─────────────────────────────────────────────────────────────

class TestListDocuments:
    async def test_returns_documents_for_existing_customer(self, service_with_mocks):
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)
        doc_repo.get_by_customer.return_value = [make_document(), make_document()]

        result = await svc.list_documents(customer_id)

        assert len(result) == 2

    async def test_raises_404_for_unknown_customer(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.list_documents(uuid.uuid4())

        assert exc_info.value.status_code == 404


# ── upload_document ────────────────────────────────────────────────────────────

class TestUploadDocument:
    async def test_raises_422_on_invalid_mime_type(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()
        file = make_upload_file("text/plain", "notas.txt")

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_document(uuid.uuid4(), file, "other", None)

        assert exc_info.value.status_code == 422

    async def test_raises_422_on_disallowed_extension(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()
        # MIME is allowed but extension is not
        file = make_upload_file("application/pdf", "malware.exe")

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_document(uuid.uuid4(), file, "other", None)

        assert exc_info.value.status_code == 422

    async def test_raises_422_when_mime_type_is_none(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()
        file = make_upload_file(None, "document.pdf")

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_document(uuid.uuid4(), file, "contract", None)

        assert exc_info.value.status_code == 422

    async def test_raises_413_when_file_exceeds_size_limit(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()
        oversized_content = b"x" * (11 * 1024 * 1024)  # 11 MB > 10 MB default limit
        file = make_upload_file("application/pdf", "grande.pdf", oversized_content)

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_document(uuid.uuid4(), file, "contract", None)

        assert exc_info.value.status_code == 413

    async def test_raises_404_when_customer_not_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None
        file = make_upload_file("application/pdf", "doc.pdf")

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_document(uuid.uuid4(), file, "contract", None)

        assert exc_info.value.status_code == 404

    async def test_saves_file_and_registers_document(self, service_with_mocks, tmp_path):
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)
        doc = make_document(customer_id=customer_id)
        doc_repo.create.return_value = doc
        file = make_upload_file("application/pdf", "contrato.pdf", b"pdf content")

        with patch("app.services.customer.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            result = await svc.upload_document(customer_id, file, "contract", "Contrato firmado")

        doc_repo.create.assert_called_once()

    async def test_uses_original_filename_as_document_name_when_no_name_given(
        self, service_with_mocks, tmp_path
    ):
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)
        doc_repo.create.return_value = make_document(customer_id=customer_id)
        file = make_upload_file("application/pdf", "mi_contrato.pdf", b"data")

        with patch("app.services.customer.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_settings.MAX_UPLOAD_SIZE_MB = 10
            await svc.upload_document(customer_id, file, "contract", None)

        created_doc = doc_repo.create.call_args[0][0]
        assert created_doc.name == "mi_contrato.pdf"


# ── delete_document ────────────────────────────────────────────────────────────

class TestDeleteDocument:
    async def test_deletes_document_and_removes_physical_file(
        self, service_with_mocks, tmp_path
    ):
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        temp_file = tmp_path / "test.pdf"
        temp_file.write_bytes(b"file content")

        doc = make_document(customer_id=customer_id, file_path=str(temp_file))
        doc_repo.get_by_id.return_value = doc

        await svc.delete_document(customer_id, doc.id)

        doc_repo.delete.assert_called_once_with(doc)
        assert not temp_file.exists()

    async def test_deletes_document_when_physical_file_is_missing(self, service_with_mocks):
        """Should succeed even if the file on disk no longer exists."""
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        doc = make_document(
            customer_id=customer_id, file_path="/non/existent/path/file.pdf"
        )
        doc_repo.get_by_id.return_value = doc

        await svc.delete_document(customer_id, doc.id)

        doc_repo.delete.assert_called_once_with(doc)

    async def test_raises_404_when_document_not_found(self, service_with_mocks):
        svc, repo, _, doc_repo = service_with_mocks
        doc_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_document(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_document_belongs_to_other_customer(
        self, service_with_mocks
    ):
        svc, repo, _, doc_repo = service_with_mocks
        doc = make_document(customer_id=uuid.uuid4())
        doc_repo.get_by_id.return_value = doc

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_document(uuid.uuid4(), doc.id)

        assert exc_info.value.status_code == 404

    async def test_commits_session(self, service_with_mocks, mock_session):
        svc, repo, _, doc_repo = service_with_mocks
        customer_id = uuid.uuid4()
        doc = make_document(customer_id=customer_id, file_path="/nope.pdf")
        doc_repo.get_by_id.return_value = doc

        await svc.delete_document(customer_id, doc.id)

        mock_session.commit.assert_called_once()


# ── get_timeline ───────────────────────────────────────────────────────────────

class TestGetTimeline:
    async def test_raises_404_when_customer_not_found(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_timeline(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_returns_timeline_with_correct_customer_id(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)

        with (
            patch.object(svc, "_get_site_visit_events", return_value=[]),
            patch.object(svc, "_get_budget_events", return_value=[]),
            patch.object(svc, "_get_work_order_events", return_value=[]),
            patch.object(svc, "_get_invoice_events", return_value=[]),
        ):
            result = await svc.get_timeline(customer_id)

        assert result.customer_id == customer_id
        assert result.events == []

    async def test_events_are_sorted_most_recent_first(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        customer_id = uuid.uuid4()
        repo.get_by_id.return_value = make_customer(id=customer_id)

        early = datetime(2024, 1, 1, tzinfo=timezone.utc)
        late = datetime(2024, 6, 1, tzinfo=timezone.utc)

        early_event = make_timeline_event(early)
        late_event = make_timeline_event(late)

        with (
            patch.object(svc, "_get_site_visit_events", return_value=[early_event]),
            patch.object(svc, "_get_budget_events", return_value=[late_event]),
            patch.object(svc, "_get_work_order_events", return_value=[]),
            patch.object(svc, "_get_invoice_events", return_value=[]),
        ):
            result = await svc.get_timeline(customer_id)

        assert result.events[0].event_date == late
        assert result.events[1].event_date == early

    async def test_aggregates_events_from_all_modules(self, service_with_mocks):
        svc, repo, *_ = service_with_mocks
        repo.get_by_id.return_value = make_customer()

        ev = make_timeline_event(datetime(2024, 3, 1, tzinfo=timezone.utc))

        with (
            patch.object(svc, "_get_site_visit_events", return_value=[ev]),
            patch.object(svc, "_get_budget_events", return_value=[ev]),
            patch.object(svc, "_get_work_order_events", return_value=[ev]),
            patch.object(svc, "_get_invoice_events", return_value=[ev]),
        ):
            result = await svc.get_timeline(uuid.uuid4())

        assert len(result.events) == 4


# ── _build_summary ─────────────────────────────────────────────────────────────

class TestBuildSummary:
    async def test_uses_default_address_as_primary(self, service_with_mocks):
        svc, *_ = service_with_mocks
        addr_default = make_address(is_default=True)
        addr_other = make_address(is_default=False)
        customer = make_customer(addresses=[addr_other, addr_default])

        summary = await svc._build_summary(customer)

        assert summary.primary_address is not None
        assert summary.primary_address.is_default is True

    async def test_falls_back_to_first_address_when_none_is_default(self, service_with_mocks):
        svc, *_ = service_with_mocks
        addr = make_address(is_default=False)
        customer = make_customer(addresses=[addr])

        summary = await svc._build_summary(customer)

        assert summary.primary_address is not None

    async def test_primary_address_is_none_for_customers_without_addresses(
        self, service_with_mocks
    ):
        svc, *_ = service_with_mocks
        customer = make_customer(addresses=[])

        summary = await svc._build_summary(customer)

        assert summary.primary_address is None

    async def test_placeholder_metrics_are_zero(self, service_with_mocks):
        svc, *_ = service_with_mocks
        customer = make_customer()

        summary = await svc._build_summary(customer)

        assert summary.active_work_orders == 0
        assert summary.total_billed == Decimal("0.00")
        assert summary.pending_amount == Decimal("0.00")

    async def test_last_activity_matches_updated_at(self, service_with_mocks):
        svc, *_ = service_with_mocks
        updated_at = datetime(2024, 5, 15, tzinfo=timezone.utc)
        customer = make_customer(updated_at=updated_at)

        summary = await svc._build_summary(customer)

        assert summary.last_activity_at == updated_at
