# Import all models here so Alembic can detect them in autogenerate
from app.models.base import TimestampMixin, UUIDMixin  # noqa: F401
from app.models.inventory_item import InventoryItem  # noqa: F401
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.user import User  # noqa: F401

# Phase 1 — added as each module is implemented
# from app.models.customer import Customer
# from app.models.site_visit import SiteVisit, SiteVisitMaterial, SiteVisitDocument
# from app.models.budget import Budget, BudgetLine
# from app.models.work_order import WorkOrder, Task, TaskMaterial
# from app.models.invoice import Invoice
