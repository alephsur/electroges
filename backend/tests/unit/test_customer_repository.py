"""
Unit tests for customer repositories.

The session is mocked so no database connection is needed.
These tests verify non-trivial query-building logic and constructor behaviour.
SQL-building correctness (filters, joins, ordering) belongs to integration tests.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.sql.dml import Update

from app.repositories.customer import CustomerRepository
from app.repositories.customer_address import CustomerAddressRepository
from app.repositories.customer_document import CustomerDocumentRepository

TENANT_ID = uuid.uuid4()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def customer_repo(mock_session) -> CustomerRepository:
    return CustomerRepository(mock_session, TENANT_ID)


@pytest.fixture
def address_repo(mock_session) -> CustomerAddressRepository:
    return CustomerAddressRepository(mock_session, TENANT_ID)


@pytest.fixture
def document_repo(mock_session) -> CustomerDocumentRepository:
    return CustomerDocumentRepository(mock_session, TENANT_ID)


# ── CustomerRepository ─────────────────────────────────────────────────────────

class TestCustomerRepositoryInit:
    def test_stores_tenant_id(self, mock_session):
        repo = CustomerRepository(mock_session, TENANT_ID)
        assert repo.tenant_id == TENANT_ID

    def test_stores_session(self, mock_session):
        repo = CustomerRepository(mock_session, TENANT_ID)
        assert repo.session is mock_session

    def test_works_without_tenant_id(self, mock_session):
        repo = CustomerRepository(mock_session)
        assert repo.tenant_id is None

    def test_model_class_is_customer(self, customer_repo):
        from app.models.customer import Customer
        assert customer_repo.model is Customer


# ── CustomerAddressRepository ──────────────────────────────────────────────────

class TestCustomerAddressRepositoryInit:
    def test_stores_tenant_id(self, mock_session):
        repo = CustomerAddressRepository(mock_session, TENANT_ID)
        assert repo.tenant_id == TENANT_ID

    def test_works_without_tenant_id(self, mock_session):
        repo = CustomerAddressRepository(mock_session)
        assert repo.tenant_id is None


class TestSetDefault:
    async def test_executes_exactly_two_updates(self, address_repo, mock_session):
        """
        set_default() must perform an atomic two-step update:
        1. Reset all addresses for the customer to is_default=False
        2. Set the target address to is_default=True
        Two UPDATE statements — no more, no less.
        """
        address_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        await address_repo.set_default(address_id, customer_id)

        assert mock_session.execute.call_count == 2

    async def test_both_statements_are_update_objects(self, address_repo, mock_session):
        """Each of the two calls to session.execute must receive a DML Update statement."""
        address_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        await address_repo.set_default(address_id, customer_id)

        calls = mock_session.execute.call_args_list
        first_stmt = calls[0].args[0]
        second_stmt = calls[1].args[0]
        assert isinstance(first_stmt, Update)
        assert isinstance(second_stmt, Update)

    async def test_first_update_targets_customer_address_table(
        self, address_repo, mock_session
    ):
        """The first UPDATE (reset) must target the customer_addresses table."""
        await address_repo.set_default(uuid.uuid4(), uuid.uuid4())

        first_stmt = mock_session.execute.call_args_list[0].args[0]
        assert first_stmt.table.name == "customer_addresses"

    async def test_second_update_targets_customer_address_table(
        self, address_repo, mock_session
    ):
        """The second UPDATE (set) must also target the customer_addresses table."""
        await address_repo.set_default(uuid.uuid4(), uuid.uuid4())

        second_stmt = mock_session.execute.call_args_list[1].args[0]
        assert second_stmt.table.name == "customer_addresses"


# ── CustomerDocumentRepository ─────────────────────────────────────────────────

class TestCustomerDocumentRepositoryInit:
    def test_stores_tenant_id(self, mock_session):
        repo = CustomerDocumentRepository(mock_session, TENANT_ID)
        assert repo.tenant_id == TENANT_ID

    def test_works_without_tenant_id(self, mock_session):
        repo = CustomerDocumentRepository(mock_session)
        assert repo.tenant_id is None


# ── BaseRepository (via CustomerRepository) ────────────────────────────────────

class TestBaseRepositoryOperations:
    async def test_create_adds_to_session_and_flushes(self, customer_repo, mock_session):
        """create() must add the object to the session and flush."""
        from app.models.customer import Customer

        obj = MagicMock(spec=Customer)
        mock_session.refresh = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh.return_value = None

        await customer_repo.create(obj)

        mock_session.add.assert_called_once_with(obj)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(obj)

    async def test_update_sets_attributes_and_flushes(self, customer_repo, mock_session):
        """update() must set each key-value pair on the object and flush."""
        from app.models.customer import Customer

        obj = MagicMock(spec=Customer)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        await customer_repo.update(obj, {"name": "Nuevo", "email": "nuevo@test.com"})

        assert obj.name == "Nuevo"
        assert obj.email == "nuevo@test.com"
        mock_session.flush.assert_called_once()

    async def test_delete_removes_object_and_flushes(self, customer_repo, mock_session):
        """delete() must call session.delete and flush."""
        from app.models.customer import Customer

        obj = MagicMock(spec=Customer)
        mock_session.flush = AsyncMock()

        await customer_repo.delete(obj)

        mock_session.delete.assert_called_once_with(obj)
        mock_session.flush.assert_called_once()

    async def test_get_by_id_returns_result(self, customer_repo, mock_session):
        """get_by_id() must execute a SELECT and return the scalar result."""
        from app.models.customer import Customer

        expected = MagicMock(spec=Customer)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_result

        result = await customer_repo.get_by_id(uuid.uuid4())

        mock_session.execute.assert_called_once()
        assert result is expected

    async def test_get_by_id_returns_none_when_not_found(self, customer_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await customer_repo.get_by_id(uuid.uuid4())

        assert result is None
