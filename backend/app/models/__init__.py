# Import all models here so Alembic can detect them in autogenerate.
# Import order matters to avoid circular imports.
from app.models.base import TimestampMixin, UUIDMixin  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.inventory_item import InventoryItem  # noqa: F401
from app.models.supplier_item import SupplierItem  # noqa: F401
from app.models.stock_movement import StockMovement  # noqa: F401
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine  # noqa: F401

from app.models.customer import Customer, CustomerAddress, CustomerDocument  # noqa: F401

from app.models.site_visit import (  # noqa: F401
    SiteVisit, SiteVisitMaterial, SiteVisitPhoto, SiteVisitDocument
)

from app.models.company_settings import CompanySettings  # noqa: F401
from app.models.budget import Budget, BudgetLine  # noqa: F401

from app.models.work_order import (  # noqa: F401
    WorkOrder, Task, TaskMaterial,
    WorkOrderPurchaseOrder, Certification, CertificationItem,
)

from app.models.invoice import Invoice, InvoiceLine, Payment  # noqa: F401
from app.models.calendar_event import CalendarEvent  # noqa: F401
