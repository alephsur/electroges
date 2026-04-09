"""
Unit tests for WorkOrder Pydantic schemas.

Pure Python — no database, no mocks, no async.
Covers validators, field constraints, and schema construction for all
major schemas in the WorkOrder module.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.work_order import (
    CertificationCreate,
    CertificationItemCreate,
    DeliveryNoteCreate,
    DeliveryNoteItemCreate,
    DeliveryNoteUpdate,
    TaskCreate,
    TaskMaterialConsume,
    TaskMaterialCreate,
    TaskStatusUpdate,
    TaskUpdate,
    WorkOrderCreate,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)

_NOW = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)


# ── TaskMaterialCreate ─────────────────────────────────────────────────────────

class TestTaskMaterialCreate:
    def test_valid_minimal(self):
        tm = TaskMaterialCreate(
            inventory_item_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            estimated_quantity=Decimal("5.0"),
        )
        assert tm.unit_cost is None
        assert tm.estimated_quantity == Decimal("5.0")

    def test_valid_with_unit_cost(self):
        tm = TaskMaterialCreate(
            inventory_item_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            estimated_quantity=Decimal("3.0"),
            unit_cost=Decimal("12.50"),
        )
        assert tm.unit_cost == Decimal("12.50")

    def test_estimated_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            TaskMaterialCreate(
                inventory_item_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                estimated_quantity=Decimal("0"),
            )

    def test_estimated_quantity_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskMaterialCreate(
                inventory_item_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                estimated_quantity=Decimal("-1.0"),
            )

    def test_unit_cost_zero_allowed(self):
        tm = TaskMaterialCreate(
            inventory_item_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            estimated_quantity=Decimal("1.0"),
            unit_cost=Decimal("0"),
        )
        assert tm.unit_cost == Decimal("0")

    def test_unit_cost_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskMaterialCreate(
                inventory_item_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                estimated_quantity=Decimal("1.0"),
                unit_cost=Decimal("-0.01"),
            )


# ── TaskMaterialConsume ────────────────────────────────────────────────────────

class TestTaskMaterialConsume:
    def test_valid_positive_consumption(self):
        tc = TaskMaterialConsume(consumed_quantity=Decimal("4.5"))
        assert tc.consumed_quantity == Decimal("4.5")
        assert tc.notes is None

    def test_zero_consumption_allowed(self):
        tc = TaskMaterialConsume(consumed_quantity=Decimal("0"))
        assert tc.consumed_quantity == Decimal("0")

    def test_negative_consumption_rejected(self):
        with pytest.raises(ValidationError):
            TaskMaterialConsume(consumed_quantity=Decimal("-1"))

    def test_notes_optional(self):
        tc = TaskMaterialConsume(consumed_quantity=Decimal("1"), notes="Consumo parcial")
        assert tc.notes == "Consumo parcial"


# ── TaskCreate ─────────────────────────────────────────────────────────────────

class TestTaskCreate:
    def test_valid_minimal(self):
        t = TaskCreate(name="Instalación cuadro eléctrico")
        assert t.name == "Instalación cuadro eléctrico"
        assert t.description is None
        assert t.unit_price is None
        assert t.estimated_hours is None
        assert t.sort_order == 0

    def test_name_max_length_255(self):
        with pytest.raises(ValidationError):
            TaskCreate(name="x" * 256)

    def test_name_exactly_255_chars_accepted(self):
        t = TaskCreate(name="x" * 255)
        assert len(t.name) == 255

    def test_unit_price_zero_allowed(self):
        t = TaskCreate(name="Revisión", unit_price=Decimal("0"))
        assert t.unit_price == Decimal("0")

    def test_unit_price_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreate(name="Tarea", unit_price=Decimal("-10"))

    def test_estimated_hours_zero_allowed(self):
        t = TaskCreate(name="Tarea", estimated_hours=Decimal("0"))
        assert t.estimated_hours == Decimal("0")

    def test_estimated_hours_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreate(name="Tarea", estimated_hours=Decimal("-1"))

    def test_full_valid(self):
        t = TaskCreate(
            name="Cableado",
            description="Cableado del cuadro principal",
            unit_price=Decimal("350.00"),
            estimated_hours=Decimal("8.0"),
            sort_order=2,
        )
        assert t.sort_order == 2
        assert t.description == "Cableado del cuadro principal"


# ── TaskUpdate ─────────────────────────────────────────────────────────────────

class TestTaskUpdate:
    def test_all_fields_optional(self):
        t = TaskUpdate()
        assert t.name is None
        assert t.description is None
        assert t.unit_price is None
        assert t.estimated_hours is None
        assert t.actual_hours is None
        assert t.sort_order is None

    def test_actual_hours_zero_allowed(self):
        t = TaskUpdate(actual_hours=Decimal("0"))
        assert t.actual_hours == Decimal("0")

    def test_actual_hours_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskUpdate(actual_hours=Decimal("-2"))

    def test_name_max_length_enforced(self):
        with pytest.raises(ValidationError):
            TaskUpdate(name="y" * 256)


# ── TaskStatusUpdate ───────────────────────────────────────────────────────────

class TestTaskStatusUpdate:
    def test_valid_statuses(self):
        for s in ("pending", "in_progress", "completed", "cancelled"):
            ts = TaskStatusUpdate(status=s)
            assert ts.status == s

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            TaskStatusUpdate(status="unknown_status")

    def test_actual_hours_optional(self):
        ts = TaskStatusUpdate(status="completed")
        assert ts.actual_hours is None

    def test_actual_hours_provided(self):
        ts = TaskStatusUpdate(status="completed", actual_hours=Decimal("6.5"))
        assert ts.actual_hours == Decimal("6.5")

    def test_actual_hours_negative_rejected(self):
        with pytest.raises(ValidationError):
            TaskStatusUpdate(status="completed", actual_hours=Decimal("-1"))


# ── WorkOrderCreate ────────────────────────────────────────────────────────────

class TestWorkOrderCreate:
    def test_valid_minimal(self):
        wo = WorkOrderCreate(customer_id=uuid.uuid4())
        assert wo.address is None
        assert wo.notes is None
        assert wo.start_date is None
        assert wo.end_date is None

    def test_address_max_length_500(self):
        with pytest.raises(ValidationError):
            WorkOrderCreate(customer_id=uuid.uuid4(), address="a" * 501)

    def test_address_exactly_500_accepted(self):
        wo = WorkOrderCreate(customer_id=uuid.uuid4(), address="a" * 500)
        assert len(wo.address) == 500

    def test_full_valid(self):
        wo = WorkOrderCreate(
            customer_id=uuid.uuid4(),
            address="Calle Mayor 5, Madrid",
            notes="Instalación completa",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 2, 28),
        )
        assert wo.start_date == date(2024, 1, 15)
        assert wo.end_date == date(2024, 2, 28)


# ── WorkOrderUpdate ────────────────────────────────────────────────────────────

class TestWorkOrderUpdate:
    def test_all_optional(self):
        wu = WorkOrderUpdate()
        assert wu.address is None
        assert wu.notes is None
        assert wu.start_date is None
        assert wu.end_date is None

    def test_partial_update_valid(self):
        wu = WorkOrderUpdate(notes="Nueva nota")
        assert wu.notes == "Nueva nota"
        assert wu.address is None


# ── WorkOrderStatusUpdate ──────────────────────────────────────────────────────

class TestWorkOrderStatusUpdate:
    def test_valid_statuses(self):
        for s in ("draft", "active", "pending_closure", "closed", "cancelled"):
            ws = WorkOrderStatusUpdate(status=s)
            assert ws.status == s

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            WorkOrderStatusUpdate(status="in_progress")

    def test_notes_optional(self):
        ws = WorkOrderStatusUpdate(status="active")
        assert ws.notes is None

    def test_notes_provided(self):
        ws = WorkOrderStatusUpdate(status="closed", notes="Obra finalizada")
        assert ws.notes == "Obra finalizada"


# ── CertificationCreate ────────────────────────────────────────────────────────

class TestCertificationCreate:
    def test_valid_with_items(self):
        task_id = uuid.uuid4()
        cert = CertificationCreate(
            items=[CertificationItemCreate(task_id=task_id, amount=Decimal("500.00"))],
            notes="Primera certificación",
        )
        assert len(cert.items) == 1
        assert cert.items[0].task_id == task_id

    def test_empty_items_list_accepted(self):
        # schema allows empty items list; service enforces business rule
        cert = CertificationCreate(items=[])
        assert cert.items == []

    def test_item_amount_zero_allowed(self):
        item = CertificationItemCreate(task_id=uuid.uuid4(), amount=Decimal("0"))
        assert item.amount == Decimal("0")

    def test_item_amount_negative_rejected(self):
        with pytest.raises(ValidationError):
            CertificationItemCreate(task_id=uuid.uuid4(), amount=Decimal("-1"))

    def test_item_amount_optional(self):
        item = CertificationItemCreate(task_id=uuid.uuid4())
        assert item.amount is None


# ── DeliveryNoteCreate ─────────────────────────────────────────────────────────

class TestDeliveryNoteCreate:
    def test_valid_minimal(self):
        dn = DeliveryNoteCreate(delivery_date=date(2024, 6, 15))
        assert dn.items == []
        assert dn.requested_by is None

    def test_full_valid(self):
        dn = DeliveryNoteCreate(
            delivery_date=date(2024, 6, 15),
            requested_by="Juan García",
            notes="Entrega urgente",
            items=[
                DeliveryNoteItemCreate(
                    line_type="material",
                    description="Cable 2.5mm²",
                    quantity=Decimal("50"),
                    unit="m",
                    unit_price=Decimal("1.20"),
                )
            ],
        )
        assert len(dn.items) == 1

    def test_requested_by_max_length_255(self):
        with pytest.raises(ValidationError):
            DeliveryNoteCreate(
                delivery_date=date(2024, 6, 15),
                requested_by="x" * 256,
            )


class TestDeliveryNoteItemCreate:
    def test_valid_defaults(self):
        item = DeliveryNoteItemCreate(
            description="Cable",
            quantity=Decimal("10"),
            unit_price=Decimal("2.50"),
        )
        assert item.line_type == "material"
        assert item.unit == "ud"
        assert item.sort_order == 0

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            DeliveryNoteItemCreate(
                description="Cable",
                quantity=Decimal("0"),
                unit_price=Decimal("1.0"),
            )

    def test_unit_price_zero_allowed(self):
        item = DeliveryNoteItemCreate(
            description="Revisión",
            quantity=Decimal("1"),
            unit_price=Decimal("0"),
        )
        assert item.unit_price == Decimal("0")

    def test_unit_price_negative_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryNoteItemCreate(
                description="Item",
                quantity=Decimal("1"),
                unit_price=Decimal("-5"),
            )

    def test_valid_line_types(self):
        for lt in ("material", "labor", "other"):
            item = DeliveryNoteItemCreate(
                line_type=lt,
                description="Desc",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
            )
            assert item.line_type == lt

    def test_invalid_line_type_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryNoteItemCreate(
                line_type="unknown",
                description="Desc",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
            )

    def test_description_max_length_500(self):
        with pytest.raises(ValidationError):
            DeliveryNoteItemCreate(
                description="x" * 501,
                quantity=Decimal("1"),
                unit_price=Decimal("1"),
            )

    def test_unit_max_length_20(self):
        with pytest.raises(ValidationError):
            DeliveryNoteItemCreate(
                description="Cable",
                quantity=Decimal("1"),
                unit_price=Decimal("1"),
                unit="x" * 21,
            )


# ── DeliveryNoteUpdate ─────────────────────────────────────────────────────────

class TestDeliveryNoteUpdate:
    def test_all_optional(self):
        du = DeliveryNoteUpdate()
        assert du.delivery_date is None
        assert du.requested_by is None
        assert du.notes is None
        assert du.items is None

    def test_partial_update(self):
        du = DeliveryNoteUpdate(notes="Nota actualizada")
        assert du.notes == "Nota actualizada"
        assert du.delivery_date is None
