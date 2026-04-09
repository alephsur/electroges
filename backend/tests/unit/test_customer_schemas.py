"""
Unit tests for customer Pydantic schemas.

These tests are pure Python — no database, no mocks, no async.
They verify that schemas enforce business constraints, apply correct defaults,
and reject invalid input.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerListResponse,
    CustomerSummary,
    CustomerTimeline,
    CustomerUpdate,
    TimelineEvent,
)


# ── CustomerCreate ─────────────────────────────────────────────────────────────

class TestCustomerCreate:
    def test_defaults_to_individual_type(self):
        data = CustomerCreate(name="Juan García")
        assert data.customer_type == "individual"

    def test_optional_fields_default_to_none(self):
        data = CustomerCreate(name="Juan García")
        assert data.tax_id is None
        assert data.email is None
        assert data.phone is None
        assert data.phone_secondary is None
        assert data.contact_person is None
        assert data.notes is None
        assert data.initial_address is None

    def test_company_type(self):
        data = CustomerCreate(name="Empresa SL", customer_type="company")
        assert data.customer_type == "company"

    def test_community_type(self):
        data = CustomerCreate(name="Comunidad de Vecinos A", customer_type="community")
        assert data.customer_type == "community"

    def test_all_scalar_fields(self):
        data = CustomerCreate(
            customer_type="company",
            name="Empresa SL",
            tax_id="B12345678",
            email="info@empresa.es",
            phone="912345678",
            phone_secondary="600111222",
            contact_person="Director General",
            notes="Cliente prioritario con contrato anual",
        )
        assert data.tax_id == "B12345678"
        assert data.contact_person == "Director General"

    def test_with_initial_address(self):
        data = CustomerCreate(
            name="Test",
            initial_address=CustomerAddressCreate(
                street="Calle Mayor 1",
                city="Madrid",
                postal_code="28001",
            ),
        )
        assert data.initial_address is not None
        assert data.initial_address.city == "Madrid"

    def test_invalid_customer_type_raises(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="Test", customer_type="freelance")

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            CustomerCreate()


# ── CustomerUpdate ─────────────────────────────────────────────────────────────

class TestCustomerUpdate:
    def test_all_fields_optional(self):
        data = CustomerUpdate()
        assert data.model_fields_set == set()

    def test_partial_update_tracks_set_fields(self):
        data = CustomerUpdate(name="Nuevo Nombre")
        assert "name" in data.model_fields_set
        assert "email" not in data.model_fields_set

    def test_deactivate_flag(self):
        data = CustomerUpdate(is_active=False)
        assert data.is_active is False

    def test_reactivate_flag(self):
        data = CustomerUpdate(is_active=True)
        assert data.is_active is True

    def test_invalid_customer_type_raises(self):
        with pytest.raises(ValidationError):
            CustomerUpdate(customer_type="invalid")

    def test_model_dump_exclude_unset(self):
        data = CustomerUpdate(name="Solo nombre")
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"name": "Solo nombre"}


# ── CustomerAddressCreate ──────────────────────────────────────────────────────

class TestCustomerAddressCreate:
    def test_defaults(self):
        addr = CustomerAddressCreate(street="Calle 1", city="Madrid", postal_code="28001")
        assert addr.address_type == "service"
        assert addr.is_default is False
        assert addr.label is None
        assert addr.province is None

    def test_fiscal_type(self):
        addr = CustomerAddressCreate(
            street="Gran Vía 5",
            city="Barcelona",
            postal_code="08001",
            address_type="fiscal",
        )
        assert addr.address_type == "fiscal"

    def test_all_optional_fields(self):
        addr = CustomerAddressCreate(
            street="Avenida Norte 10",
            city="Sevilla",
            postal_code="41001",
            province="Sevilla",
            label="Oficina principal",
            is_default=True,
        )
        assert addr.province == "Sevilla"
        assert addr.label == "Oficina principal"
        assert addr.is_default is True

    def test_invalid_address_type_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(
                street="X", city="Y", postal_code="Z", address_type="home"
            )

    def test_street_is_required(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(city="Madrid", postal_code="28001")

    def test_city_is_required(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(street="Calle 1", postal_code="28001")

    def test_postal_code_is_required(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(street="Calle 1", city="Madrid")


# ── CustomerAddressUpdate ──────────────────────────────────────────────────────

class TestCustomerAddressUpdate:
    def test_all_optional(self):
        data = CustomerAddressUpdate()
        assert data.model_fields_set == set()

    def test_partial_city(self):
        data = CustomerAddressUpdate(city="Sevilla")
        assert data.city == "Sevilla"
        assert "city" in data.model_fields_set
        assert "street" not in data.model_fields_set

    def test_set_default_flag(self):
        data = CustomerAddressUpdate(is_default=True)
        assert data.is_default is True

    def test_invalid_address_type_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressUpdate(address_type="rooftop")


# ── CustomerSummary ────────────────────────────────────────────────────────────

class TestCustomerSummary:
    def _make_summary(self, **kwargs) -> CustomerSummary:
        now = datetime.now(timezone.utc)
        defaults = dict(
            id=uuid.uuid4(),
            customer_type="individual",
            name="Test",
            tax_id=None,
            email=None,
            phone=None,
            contact_person=None,
            is_active=True,
            created_at=now,
        )
        defaults.update(kwargs)
        return CustomerSummary(**defaults)

    def test_metric_defaults_to_zero(self):
        summary = self._make_summary()
        assert summary.active_work_orders == 0
        assert summary.total_billed == Decimal("0.00")
        assert summary.pending_amount == Decimal("0.00")

    def test_no_primary_address_by_default(self):
        summary = self._make_summary()
        assert summary.primary_address is None

    def test_last_activity_none_by_default(self):
        summary = self._make_summary()
        assert summary.last_activity_at is None


# ── CustomerListResponse ───────────────────────────────────────────────────────

class TestCustomerListResponse:
    def test_empty_list(self):
        response = CustomerListResponse(items=[], total=0, skip=0, limit=100)
        assert response.total == 0
        assert response.items == []
        assert response.skip == 0
        assert response.limit == 100

    def test_pagination_fields(self):
        response = CustomerListResponse(items=[], total=50, skip=20, limit=10)
        assert response.total == 50
        assert response.skip == 20
        assert response.limit == 10


# ── TimelineEvent ──────────────────────────────────────────────────────────────

class TestTimelineEvent:
    def _make_event(self, **kwargs) -> TimelineEvent:
        defaults = dict(
            event_type="site_visit",
            event_date=datetime.now(timezone.utc),
            title="Visita técnica",
            subtitle=None,
            reference_id=uuid.uuid4(),
            reference_type="site_visit",
        )
        defaults.update(kwargs)
        return TimelineEvent(**defaults)

    def test_amount_and_status_optional(self):
        event = self._make_event()
        assert event.amount is None
        assert event.status is None

    def test_monetary_event(self):
        event = self._make_event(
            event_type="invoice_paid",
            reference_type="invoice",
            amount=Decimal("1500.00"),
            status="paid",
        )
        assert event.amount == Decimal("1500.00")
        assert event.status == "paid"

    def test_all_valid_event_types(self):
        valid_types = [
            "site_visit",
            "budget_created",
            "budget_sent",
            "budget_accepted",
            "budget_rejected",
            "work_order_created",
            "work_order_closed",
            "invoice_issued",
            "invoice_paid",
        ]
        for event_type in valid_types:
            event = self._make_event(event_type=event_type, reference_type="other")
            assert event.event_type == event_type

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValidationError):
            self._make_event(event_type="unknown_event")


# ── CustomerTimeline ───────────────────────────────────────────────────────────

class TestCustomerTimeline:
    def test_empty_timeline_defaults(self):
        timeline = CustomerTimeline(customer_id=uuid.uuid4(), events=[])
        assert timeline.total_site_visits == 0
        assert timeline.total_budgets == 0
        assert timeline.total_work_orders == 0
        assert timeline.total_invoiced == Decimal("0.00")
        assert timeline.total_pending == Decimal("0.00")

    def test_stores_customer_id(self):
        customer_id = uuid.uuid4()
        timeline = CustomerTimeline(customer_id=customer_id, events=[])
        assert timeline.customer_id == customer_id

    def test_events_list(self):
        event = TimelineEvent(
            event_type="site_visit",
            event_date=datetime.now(timezone.utc),
            title="Visita",
            subtitle=None,
            reference_id=uuid.uuid4(),
            reference_type="site_visit",
        )
        timeline = CustomerTimeline(customer_id=uuid.uuid4(), events=[event])
        assert len(timeline.events) == 1
