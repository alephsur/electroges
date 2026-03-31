import logging
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer, CustomerAddress, CustomerDocument
from app.repositories.customer import CustomerRepository
from app.repositories.customer_address import CustomerAddressRepository
from app.repositories.customer_document import CustomerDocumentRepository
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerDocumentResponse,
    CustomerListResponse,
    CustomerResponse,
    CustomerSummary,
    CustomerTimeline,
    CustomerUpdate,
    TimelineEvent,
)

logger = logging.getLogger(__name__)


class CustomerService:
    def __init__(self, session: AsyncSession):
        self._repo = CustomerRepository(session)
        self._addr_repo = CustomerAddressRepository(session)
        self._doc_repo = CustomerDocumentRepository(session)
        self._session = session

    # ── List / detail ─────────────────────────────────────────────────────────

    async def list_customers(
        self,
        q: str | None = None,
        customer_type: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> CustomerListResponse:
        logger.info(
            "Listing customers [q=%r, type=%s, is_active=%s, skip=%d, limit=%d]",
            q, customer_type, is_active, skip, limit,
        )
        customers, total = await self._repo.search(
            query=q,
            customer_type=customer_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        summaries = [await self._build_summary(c) for c in customers]
        return CustomerListResponse(items=summaries, total=total, skip=skip, limit=limit)

    async def get_customer(self, customer_id: uuid.UUID) -> CustomerResponse:
        logger.info("Fetching customer id=%s", customer_id)
        customer = await self._repo.get_with_detail(customer_id)
        if not customer:
            logger.warning("Customer not found: id=%s", customer_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )
        return await self._build_response(customer)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        logger.info("Creating customer name=%r tax_id=%r", data.name, data.tax_id)
        if data.tax_id:
            await self._assert_tax_id_unique(data.tax_id)

        customer = Customer(**data.model_dump(exclude={"initial_address"}))
        customer = await self._repo.create(customer)

        # Create initial address if provided and mark it as default
        if data.initial_address:
            addr_data = data.initial_address.model_dump()
            addr_data["is_default"] = True
            address = CustomerAddress(customer_id=customer.id, **addr_data)
            await self._addr_repo.create(address)

        await self._session.commit()
        logger.info("Customer created id=%s", customer.id)
        return await self.get_customer(customer.id)

    async def update_customer(
        self, customer_id: uuid.UUID, data: CustomerUpdate
    ) -> CustomerResponse:
        logger.info("Updating customer id=%s fields=%s", customer_id, list(data.model_fields_set))
        customer = await self._repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        update_data = data.model_dump(exclude_unset=True)

        # Validate tax_id uniqueness if it is being changed
        new_tax_id = update_data.get("tax_id")
        if new_tax_id and new_tax_id != customer.tax_id:
            await self._assert_tax_id_unique(new_tax_id)

        await self._repo.update(customer, update_data)
        await self._session.commit()
        logger.info("Customer updated id=%s", customer_id)
        return await self.get_customer(customer_id)

    async def deactivate_customer(self, customer_id: uuid.UUID) -> None:
        """
        Soft delete. Sets is_active = False.
        TODO: When WorkOrder module exists, verify no active work orders before deactivating.
        """
        logger.info("Deactivating customer id=%s", customer_id)
        customer = await self._repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )
        # TODO: check for active work orders when WorkOrder module is implemented
        await self._repo.update(customer, {"is_active": False})
        await self._session.commit()
        logger.info("Customer deactivated id=%s", customer_id)

    # ── Addresses ─────────────────────────────────────────────────────────────

    async def list_addresses(self, customer_id: uuid.UUID) -> list[CustomerAddressResponse]:
        await self._assert_customer_exists(customer_id)
        addresses = await self._addr_repo.get_by_customer(customer_id)
        return [CustomerAddressResponse.model_validate(a) for a in addresses]

    async def add_address(
        self, customer_id: uuid.UUID, data: CustomerAddressCreate
    ) -> CustomerAddressResponse:
        await self._assert_customer_exists(customer_id)

        address = CustomerAddress(customer_id=customer_id, **data.model_dump())
        address = await self._addr_repo.create(address)

        existing = await self._addr_repo.get_by_customer(customer_id)
        # Mark as default if it is the only one or explicitly requested
        if len(existing) == 1 or data.is_default:
            await self._addr_repo.set_default(address.id, customer_id)
            await self._session.flush()
            await self._session.refresh(address)

        await self._session.commit()
        return CustomerAddressResponse.model_validate(address)

    async def update_address(
        self,
        customer_id: uuid.UUID,
        address_id: uuid.UUID,
        data: CustomerAddressUpdate,
    ) -> CustomerAddressResponse:
        address = await self._addr_repo.get_by_id(address_id)
        if not address or address.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dirección no encontrada",
            )

        update_data = data.model_dump(exclude_unset=True)

        if update_data.pop("is_default", None):
            await self._addr_repo.set_default(address_id, customer_id)

        if update_data:
            await self._addr_repo.update(address, update_data)

        await self._session.commit()
        await self._session.refresh(address)
        return CustomerAddressResponse.model_validate(address)

    async def delete_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> None:
        address = await self._addr_repo.get_by_id(address_id)
        if not address or address.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dirección no encontrada",
            )

        existing = await self._addr_repo.get_by_customer(customer_id)
        if len(existing) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la única dirección del cliente. "
                       "Añade otra dirección antes de eliminar esta.",
            )

        await self._addr_repo.delete(address)
        await self._session.commit()

    async def set_default_address(
        self, customer_id: uuid.UUID, address_id: uuid.UUID
    ) -> CustomerAddressResponse:
        address = await self._addr_repo.get_by_id(address_id)
        if not address or address.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dirección no encontrada",
            )
        await self._addr_repo.set_default(address_id, customer_id)
        await self._session.commit()
        await self._session.refresh(address)
        return CustomerAddressResponse.model_validate(address)

    # ── Documents ─────────────────────────────────────────────────────────────

    async def list_documents(self, customer_id: uuid.UUID) -> list[CustomerDocumentResponse]:
        await self._assert_customer_exists(customer_id)
        docs = await self._doc_repo.get_by_customer(customer_id)
        return [CustomerDocumentResponse.model_validate(d) for d in docs]

    async def upload_document(
        self,
        customer_id: uuid.UUID,
        file: UploadFile,
        document_type: str,
        name: str | None,
    ) -> CustomerDocumentResponse:
        """
        Saves the file to uploads/customers/{customer_id}/
        and registers the document in the database.
        """
        await self._assert_customer_exists(customer_id)

        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el tamaño máximo permitido de {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )

        upload_dir = Path(settings.UPLOAD_DIR) / "customers" / str(customer_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = upload_dir / safe_filename
        file_path.write_bytes(content)

        doc = CustomerDocument(
            customer_id=customer_id,
            name=name or file.filename or safe_filename,
            file_path=str(file_path),
            file_size_bytes=len(content),
            document_type=document_type,
        )
        doc = await self._doc_repo.create(doc)
        await self._session.commit()
        logger.info("Document uploaded customer_id=%s doc_id=%s", customer_id, doc.id)
        return CustomerDocumentResponse.model_validate(doc)

    async def delete_document(self, customer_id: uuid.UUID, document_id: uuid.UUID) -> None:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc or doc.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado",
            )

        # Remove physical file if it exists
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

        await self._doc_repo.delete(doc)
        await self._session.commit()
        logger.info("Document deleted customer_id=%s doc_id=%s", customer_id, document_id)

    # ── Timeline ──────────────────────────────────────────────────────────────

    async def get_timeline(self, customer_id: uuid.UUID) -> CustomerTimeline:
        """
        Builds the unified customer timeline by aggregating events from all modules.

        IMPORTANT: at this phase only the Customer module exists. SiteVisit, Budget,
        WorkOrder and Invoice modules are not implemented yet. Each _get_*_events()
        method returns [] until its module is implemented.
        """
        await self._assert_customer_exists(customer_id)

        events: list[TimelineEvent] = []
        events += await self._get_site_visit_events(customer_id)
        events += await self._get_budget_events(customer_id)
        events += await self._get_work_order_events(customer_id)   # TODO: WorkOrder module
        events += await self._get_invoice_events(customer_id)      # TODO: Invoice module

        events.sort(key=lambda e: e.event_date, reverse=True)

        return CustomerTimeline(
            customer_id=customer_id,
            events=events,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_customer_exists(self, customer_id: uuid.UUID) -> None:
        customer = await self._repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

    async def _assert_tax_id_unique(self, tax_id: str) -> None:
        existing = await self._repo.get_by_tax_id(tax_id)
        if existing:
            logger.warning("Duplicate tax_id rejected: %r (existing id=%s)", tax_id, existing.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un cliente con el NIF/CIF '{tax_id}'",
            )

    async def _build_summary(self, customer: Customer) -> CustomerSummary:
        """
        Calculates metrics for the list view.
        Returns default values (0) in this phase.
        Will be enriched when WorkOrder and Invoice modules exist.
        """
        primary_address = next(
            (a for a in customer.addresses if a.is_default),
            customer.addresses[0] if customer.addresses else None,
        )
        return CustomerSummary(
            id=customer.id,
            customer_type=customer.customer_type,
            name=customer.name,
            tax_id=customer.tax_id,
            email=customer.email,
            phone=customer.phone,
            contact_person=customer.contact_person,
            is_active=customer.is_active,
            active_work_orders=0,           # TODO: count active WorkOrders
            total_billed=Decimal("0.00"),   # TODO: sum paid Invoices
            pending_amount=Decimal("0.00"), # TODO: sum pending Invoices
            last_activity_at=customer.updated_at,
            primary_address=(
                CustomerAddressResponse.model_validate(primary_address)
                if primary_address else None
            ),
            created_at=customer.created_at,
        )

    async def _build_response(self, customer: Customer) -> CustomerResponse:
        summary = await self._build_summary(customer)
        return CustomerResponse(
            **summary.model_dump(),
            phone_secondary=customer.phone_secondary,
            notes=customer.notes,
            addresses=[CustomerAddressResponse.model_validate(a) for a in customer.addresses],
            documents=[CustomerDocumentResponse.model_validate(d) for d in customer.documents],
            updated_at=customer.updated_at,
        )

    async def _get_site_visit_events(self, customer_id: uuid.UUID) -> list[TimelineEvent]:
        from app.repositories.site_visit import SiteVisitRepository
        visit_repo = SiteVisitRepository(self._session)
        visits = await visit_repo.get_by_customer(customer_id, skip=0, limit=100)
        events = []
        for v in visits:
            events.append(TimelineEvent(
                event_type="site_visit",
                event_date=v.visit_date,
                title=f"Visita técnica — {v.address_text or 'Sin dirección'}",
                subtitle="Estado: " + v.status.value + (
                    f" · Presupuesto orientativo: {v.estimated_budget}€"
                    if v.estimated_budget else ""
                ),
                reference_id=v.id,
                reference_type="site_visit",
                amount=v.estimated_budget,
                status=v.status.value,
            ))
        return events

    async def _get_budget_events(self, customer_id: uuid.UUID) -> list[TimelineEvent]:
        from datetime import datetime as dt, timezone

        from app.repositories.budget import BudgetRepository
        from app.services.budget import BudgetService

        budget_repo = BudgetRepository(self._session)
        budgets = await budget_repo.get_by_customer(customer_id, latest_only=True)
        svc = BudgetService(self._session)
        events = []
        for b in budgets:
            effective_status = svc._get_effective_status(b)
            totals = svc._calculate_totals(b)
            events.append(
                TimelineEvent(
                    event_type="budget_created",
                    event_date=dt.combine(b.issue_date, dt.min.time(), tzinfo=timezone.utc),
                    title=f"Presupuesto {b.budget_number}",
                    subtitle=f"Estado: {effective_status} · Total: {totals.total:.2f}€",
                    reference_id=b.id,
                    reference_type="budget",
                    amount=totals.total,
                    status=effective_status,
                )
            )
        return events

    async def _get_work_order_events(self, customer_id: uuid.UUID) -> list[TimelineEvent]:
        from app.repositories.work_order import WorkOrderRepository

        repo = WorkOrderRepository(self._session)
        orders = await repo.get_by_customer(customer_id)
        events = []
        for o in orders:
            events.append(TimelineEvent(
                event_type="work_order_created",
                event_date=o.created_at,
                title=f"Obra {o.work_order_number}",
                subtitle="Estado: " + o.status.value + (
                    f" · {o.address}" if o.address else ""
                ),
                reference_id=o.id,
                reference_type="work_order",
                status=o.status.value,
            ))
            if o.status.value == "closed":
                events.append(TimelineEvent(
                    event_type="work_order_closed",
                    event_date=o.updated_at,
                    title=f"Obra {o.work_order_number} cerrada",
                    subtitle=None,
                    reference_id=o.id,
                    reference_type="work_order",
                    status="closed",
                ))
        return events

    async def _get_invoice_events(self, customer_id: uuid.UUID) -> list[TimelineEvent]:
        # TODO: implement when Invoice module exists
        return []
