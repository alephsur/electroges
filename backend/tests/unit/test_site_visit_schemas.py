"""
Unit tests for site visit Pydantic schemas.

Pure Python — no database, no mocks, no async.
Covers business-rule validators built into the schemas:
  - SiteVisitMaterialCreate requires item or free-text description
  - SiteVisitCreate requires contact name when no customer, and an address
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.site_visit import (
    SiteVisitCreate,
    SiteVisitLinkCustomer,
    SiteVisitListResponse,
    SiteVisitMaterialCreate,
    SiteVisitMaterialUpdate,
    SiteVisitPhotoUpdate,
    SiteVisitReorderPhotos,
    SiteVisitStatusUpdate,
    SiteVisitUpdate,
)

_NOW = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)


# ── SiteVisitMaterialCreate ────────────────────────────────────────────────────

class TestSiteVisitMaterialCreate:
    def test_accepts_free_text_description(self):
        m = SiteVisitMaterialCreate(description="Cable 2.5mm²", estimated_qty=Decimal("10"))
        assert m.description == "Cable 2.5mm²"
        assert m.inventory_item_id is None

    def test_accepts_inventory_item_id(self):
        item_id = uuid.uuid4()
        m = SiteVisitMaterialCreate(inventory_item_id=item_id, estimated_qty=Decimal("5"))
        assert m.inventory_item_id == item_id
        assert m.description is None

    def test_accepts_both_description_and_item(self):
        m = SiteVisitMaterialCreate(
            inventory_item_id=uuid.uuid4(),
            description="Nota adicional",
            estimated_qty=Decimal("3"),
        )
        assert m.description == "Nota adicional"

    def test_raises_when_neither_description_nor_item(self):
        with pytest.raises(ValidationError) as exc_info:
            SiteVisitMaterialCreate(estimated_qty=Decimal("5"))
        assert "inventario" in str(exc_info.value).lower() or "descripción" in str(exc_info.value).lower()

    def test_optional_unit_and_cost_default_to_none(self):
        m = SiteVisitMaterialCreate(description="Cable", estimated_qty=Decimal("1"))
        assert m.unit is None
        assert m.unit_cost is None

    def test_all_optional_fields(self):
        m = SiteVisitMaterialCreate(
            description="Cable",
            estimated_qty=Decimal("10"),
            unit="m",
            unit_cost=Decimal("1.50"),
        )
        assert m.unit == "m"
        assert m.unit_cost == Decimal("1.50")


# ── SiteVisitMaterialUpdate ────────────────────────────────────────────────────

class TestSiteVisitMaterialUpdate:
    def test_all_fields_optional(self):
        data = SiteVisitMaterialUpdate()
        assert data.model_fields_set == set()

    def test_partial_update_tracks_set_fields(self):
        data = SiteVisitMaterialUpdate(estimated_qty=Decimal("20"))
        assert "estimated_qty" in data.model_fields_set
        assert "unit" not in data.model_fields_set

    def test_model_dump_exclude_unset(self):
        data = SiteVisitMaterialUpdate(unit="ud")
        assert data.model_dump(exclude_unset=True) == {"unit": "ud"}


# ── SiteVisitCreate ────────────────────────────────────────────────────────────

class TestSiteVisitCreate:
    def _make_valid_anonymous(self, **kwargs) -> dict:
        """Minimum valid payload for a visit without a registered customer."""
        defaults = dict(
            contact_name="Propietario sin registrar",
            address_text="Calle Mayor 1, Madrid",
            visit_date=_NOW,
        )
        defaults.update(kwargs)
        return defaults

    def _make_valid_registered(self, **kwargs) -> dict:
        """Minimum valid payload for a visit with a registered customer."""
        defaults = dict(
            customer_id=uuid.uuid4(),
            address_text="Calle Mayor 1, Madrid",
            visit_date=_NOW,
        )
        defaults.update(kwargs)
        return defaults

    def test_valid_anonymous_visit(self):
        data = SiteVisitCreate(**self._make_valid_anonymous())
        assert data.contact_name == "Propietario sin registrar"
        assert data.customer_id is None

    def test_valid_registered_customer_visit(self):
        data = SiteVisitCreate(**self._make_valid_registered())
        assert data.customer_id is not None

    def test_customer_address_id_replaces_address_text(self):
        data = SiteVisitCreate(
            customer_id=uuid.uuid4(),
            customer_address_id=uuid.uuid4(),
            visit_date=_NOW,
        )
        assert data.customer_address_id is not None
        assert data.address_text is None

    def test_raises_when_no_customer_and_no_contact_name(self):
        with pytest.raises(ValidationError) as exc_info:
            SiteVisitCreate(address_text="Calle 1", visit_date=_NOW)
        assert "contacto" in str(exc_info.value).lower()

    def test_raises_when_no_address_and_no_customer_address_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SiteVisitCreate(contact_name="Juan", visit_date=_NOW)
        assert "dirección" in str(exc_info.value).lower()

    def test_optional_technical_fields_default_to_none(self):
        data = SiteVisitCreate(**self._make_valid_anonymous())
        assert data.description is None
        assert data.work_scope is None
        assert data.technical_notes is None
        assert data.estimated_hours is None
        assert data.estimated_budget is None
        assert data.estimated_duration_hours is None

    def test_all_technical_fields(self):
        data = SiteVisitCreate(
            **self._make_valid_anonymous(
                description="Instalación eléctrica completa",
                work_scope="Cuadro + circuitos",
                technical_notes="Vivienda de 90m²",
                estimated_hours=Decimal("8"),
                estimated_budget=Decimal("1500.00"),
                estimated_duration_hours=Decimal("4.5"),
            )
        )
        assert data.estimated_budget == Decimal("1500.00")
        assert data.estimated_duration_hours == Decimal("4.5")

    def test_visit_date_is_required(self):
        with pytest.raises(ValidationError):
            SiteVisitCreate(contact_name="Juan", address_text="Calle 1")


# ── SiteVisitUpdate ────────────────────────────────────────────────────────────

class TestSiteVisitUpdate:
    def test_all_fields_optional(self):
        data = SiteVisitUpdate()
        assert data.model_fields_set == set()

    def test_partial_update(self):
        data = SiteVisitUpdate(description="Nueva descripción")
        assert data.description == "Nueva descripción"
        assert "description" in data.model_fields_set
        assert "work_scope" not in data.model_fields_set

    def test_model_dump_exclude_unset(self):
        data = SiteVisitUpdate(technical_notes="Nota", estimated_budget=Decimal("800"))
        dumped = data.model_dump(exclude_unset=True)
        assert set(dumped.keys()) == {"technical_notes", "estimated_budget"}


# ── SiteVisitStatusUpdate ──────────────────────────────────────────────────────

class TestSiteVisitStatusUpdate:
    @pytest.mark.parametrize("s", ["scheduled", "in_progress", "completed", "cancelled", "no_show"])
    def test_valid_statuses(self, s):
        data = SiteVisitStatusUpdate(status=s)
        assert data.status == s

    def test_optional_notes(self):
        data = SiteVisitStatusUpdate(status="completed")
        assert data.notes is None

    def test_notes_with_status(self):
        data = SiteVisitStatusUpdate(status="cancelled", notes="Cliente no disponible")
        assert data.notes == "Cliente no disponible"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SiteVisitStatusUpdate(status="unknown")


# ── SiteVisitLinkCustomer ──────────────────────────────────────────────────────

class TestSiteVisitLinkCustomer:
    def test_customer_id_required(self):
        with pytest.raises(ValidationError):
            SiteVisitLinkCustomer()

    def test_valid_without_address(self):
        data = SiteVisitLinkCustomer(customer_id=uuid.uuid4())
        assert data.customer_address_id is None

    def test_valid_with_address(self):
        data = SiteVisitLinkCustomer(
            customer_id=uuid.uuid4(), customer_address_id=uuid.uuid4()
        )
        assert data.customer_address_id is not None


# ── SiteVisitReorderPhotos ─────────────────────────────────────────────────────

class TestSiteVisitReorderPhotos:
    def test_accepts_list_of_uuids(self):
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        data = SiteVisitReorderPhotos(photo_ids=ids)
        assert len(data.photo_ids) == 3

    def test_accepts_empty_list(self):
        data = SiteVisitReorderPhotos(photo_ids=[])
        assert data.photo_ids == []


# ── SiteVisitPhotoUpdate ───────────────────────────────────────────────────────

class TestSiteVisitPhotoUpdate:
    def test_all_optional(self):
        data = SiteVisitPhotoUpdate()
        assert data.model_fields_set == set()

    def test_caption_and_sort_order(self):
        data = SiteVisitPhotoUpdate(caption="Vista frontal", sort_order=2)
        assert data.caption == "Vista frontal"
        assert data.sort_order == 2


# ── SiteVisitListResponse ──────────────────────────────────────────────────────

class TestSiteVisitListResponse:
    def test_empty_response(self):
        r = SiteVisitListResponse(items=[], total=0, skip=0, limit=50)
        assert r.total == 0
        assert r.items == []

    def test_pagination_fields(self):
        r = SiteVisitListResponse(items=[], total=100, skip=50, limit=25)
        assert r.total == 100
        assert r.skip == 50
        assert r.limit == 25
