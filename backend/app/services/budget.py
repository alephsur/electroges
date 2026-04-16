"""Budget service — all business logic for the Budget module."""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.budget import Budget, BudgetLine, BudgetStatus
from app.repositories.budget import BudgetLineRepository, BudgetRepository
from app.repositories.company_settings import CompanySettingsRepository
from app.repositories.customer import CustomerRepository
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.site_visit import SiteVisitRepository
from app.schemas.budget import (
    BudgetCreate,
    BudgetFromVisitRequest,
    BudgetLineCreate,
    BudgetLineInternalResponse,
    BudgetLinePublicResponse,
    BudgetListResponse,
    BudgetResponse,
    BudgetSummary,
    BudgetTotals,
    BudgetUpdate,
    BudgetVersionInfo,
    ReorderLinesRequest,
    WorkOrderPreview,
)

logger = logging.getLogger(__name__)


class BudgetService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id
        self._repo = BudgetRepository(session, tenant_id)
        self._line_repo = BudgetLineRepository(session, tenant_id)
        self._company_repo = CompanySettingsRepository(session, tenant_id)
        self._customer_repo = CustomerRepository(session, tenant_id)
        self._item_repo = InventoryItemRepository(session, tenant_id)
        self._visit_repo = SiteVisitRepository(session, tenant_id)

    # ── List / detail ──────────────────────────────────────────────────────────

    async def list_budgets(
        self,
        q: str | None,
        customer_id: uuid.UUID | None,
        status_filter: str | None,
        date_from: date | None,
        date_to: date | None,
        latest_only: bool,
        skip: int,
        limit: int,
    ) -> BudgetListResponse:
        budgets, total = await self._repo.search(
            query=q,
            customer_id=customer_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
            latest_only=latest_only,
            skip=skip,
            limit=limit,
        )
        return BudgetListResponse(
            items=[self._build_summary(b) for b in budgets],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_budget(self, budget_id: uuid.UUID) -> BudgetResponse:
        budget = await self._repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        return self._build_response(budget)

    async def get_budget_versions(self, budget_id: uuid.UUID) -> list[BudgetVersionInfo]:
        chain = await self._repo.get_version_chain(budget_id)
        return [self._build_version_info(b) for b in chain]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_budget(self, data: BudgetCreate) -> BudgetResponse:
        """Create a budget directly (with or without a site visit or customer)."""
        company = await self._company_repo.get()

        if data.customer_id is not None:
            customer = await self._customer_repo.get_by_id(data.customer_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado",
                )

        budget_number = await self._repo.get_next_budget_number()
        today = date.today()

        budget = Budget(
            budget_number=budget_number,
            version=1,
            customer_id=data.customer_id,
            site_visit_id=data.site_visit_id,
            status=BudgetStatus.DRAFT,
            issue_date=data.issue_date or today,
            valid_until=data.valid_until or (today + timedelta(days=company.default_validity_days)),
            tax_rate=data.tax_rate or company.default_tax_rate,
            discount_pct=data.discount_pct,
            notes=data.notes,
            client_notes=data.client_notes,
            tenant_id=self._tenant_id,
        )
        budget = await self._repo.create(budget)

        for i, line_data in enumerate(data.lines):
            await self._create_line(budget.id, line_data, sort_order=i)

        await self._session.commit()
        logger.info("Budget created id=%s number=%s", budget.id, budget_number)
        return await self.get_budget(budget.id)

    async def create_budget_from_visit(self, data: BudgetFromVisitRequest) -> BudgetResponse:
        """Create a budget from a completed site visit with auto-preloaded lines."""
        from app.models.site_visit import SiteVisit, SiteVisitMaterial
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select

        # Eagerly load materials and their inventory items
        result = await self._session.execute(
            select(SiteVisit)
            .options(
                selectinload(SiteVisit.materials).selectinload(SiteVisitMaterial.inventory_item)
            )
            .where(SiteVisit.id == data.site_visit_id)
        )
        visit = result.scalar_one_or_none()

        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita técnica no encontrada",
            )
        if visit.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede crear un presupuesto desde una visita completada",
            )

        company = await self._company_repo.get()
        today = date.today()
        budget_number = await self._repo.get_next_budget_number()

        budget = Budget(
            budget_number=budget_number,
            version=1,
            customer_id=visit.customer_id,
            site_visit_id=visit.id,
            status=BudgetStatus.DRAFT,
            issue_date=today,
            valid_until=data.valid_until or (today + timedelta(days=company.default_validity_days)),
            tax_rate=data.tax_rate or company.default_tax_rate,
            discount_pct=data.discount_pct,
            notes=data.notes,
            client_notes=data.client_notes,
            tenant_id=self._tenant_id,
        )
        budget = await self._repo.create(budget)

        if data.lines_override is not None:
            lines_to_create = data.lines_override
        else:
            lines_to_create = self._lines_from_visit(visit)

        for i, line_data in enumerate(lines_to_create):
            await self._create_line(budget.id, line_data, sort_order=i)

        await self._session.commit()
        logger.info(
            "Budget created from visit id=%s number=%s visit_id=%s",
            budget.id, budget_number, visit.id,
        )
        return await self.get_budget(budget.id)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update_budget(self, budget_id: uuid.UUID, data: BudgetUpdate) -> BudgetResponse:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden editar presupuestos en estado borrador. "
                       "Si necesitas modificarlo, crea una nueva versión.",
            )
        await self._repo.update(budget, data.model_dump(exclude_none=True))
        await self._session.commit()
        return await self.get_budget(budget_id)

    # ── Status lifecycle ───────────────────────────────────────────────────────

    async def send_budget(self, budget_id: uuid.UUID) -> BudgetResponse:
        budget = await self._repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden enviar presupuestos en estado borrador",
            )
        if not budget.lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede enviar un presupuesto sin líneas",
            )
        await self._repo.update(budget, {"status": BudgetStatus.SENT})
        await self._session.commit()
        return await self.get_budget(budget_id)

    async def reject_budget(self, budget_id: uuid.UUID, notes: str | None) -> BudgetResponse:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden rechazar presupuestos en estado enviado",
            )
        update_data: dict = {"status": BudgetStatus.REJECTED}
        if notes:
            update_data["notes"] = (budget.notes or "") + f"\n[Rechazo] {notes}"
        await self._repo.update(budget, update_data)
        await self._session.commit()
        return await self.get_budget(budget_id)

    # ── Versioning ─────────────────────────────────────────────────────────────

    async def create_new_version(self, budget_id: uuid.UUID) -> BudgetResponse:
        """
        Creates a new version by copying all lines from the previous version.
        The previous version is marked as is_latest_version=False.
        Only sent or rejected budgets can be versioned.
        """
        original = await self._repo.get_with_full_detail(budget_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if original.status not in (BudgetStatus.SENT, BudgetStatus.REJECTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede crear una nueva versión desde un presupuesto enviado o rechazado",
            )

        root_id = original.parent_budget_id or original.id
        new_version_number = original.version + 1
        base_number = original.budget_number.split("-v")[0]
        new_number = f"{base_number}-v{new_version_number}"

        await self._repo.mark_previous_versions_outdated(budget_id)

        company = await self._company_repo.get()
        today = date.today()

        new_budget = Budget(
            budget_number=new_number,
            version=new_version_number,
            parent_budget_id=root_id,
            is_latest_version=True,
            customer_id=original.customer_id,
            site_visit_id=original.site_visit_id,
            status=BudgetStatus.DRAFT,
            issue_date=today,
            valid_until=today + timedelta(days=company.default_validity_days),
            tax_rate=original.tax_rate,
            discount_pct=original.discount_pct,
            notes=original.notes,
            client_notes=original.client_notes,
            tenant_id=self._tenant_id,
        )
        new_budget = await self._repo.create(new_budget)

        for i, line in enumerate(original.lines):
            await self._create_line(
                new_budget.id,
                BudgetLineCreate(
                    line_type=line.line_type.value,
                    description=line.description,
                    inventory_item_id=line.inventory_item_id,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=line.unit_price,
                    unit_cost=line.unit_cost,
                    line_discount_pct=line.line_discount_pct,
                    sort_order=i,
                ),
                sort_order=i,
            )

        await self._session.commit()
        logger.info(
            "New version created budget_id=%s new_id=%s version=%d",
            budget_id, new_budget.id, new_version_number,
        )
        return await self.get_budget(new_budget.id)

    # ── Acceptance flow (two steps) ───────────────────────────────────────────

    async def get_work_order_preview(self, budget_id: uuid.UUID) -> WorkOrderPreview:
        """
        STEP 1: generates a preview of what would be created on acceptance.
        Does NOT modify anything in the database.
        """
        budget = await self._repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede aceptar un presupuesto en estado enviado",
            )

        tasks_to_create = []
        materials_to_reserve = []
        warnings = []
        total_cost = Decimal("0.0")

        for line in budget.lines:
            if line.line_type.value == "labor":
                tasks_to_create.append({
                    "name": line.description,
                    "estimated_hours": float(line.quantity),
                    "description": line.description,
                })
                total_cost += line.unit_cost * line.quantity

            elif line.line_type.value == "material":
                item = line.inventory_item
                item_name = item.name if item else line.description
                stock_available = float(item.stock_current) if item else 0.0
                enough_stock = stock_available >= float(line.quantity)

                materials_to_reserve.append({
                    "name": item_name,
                    "quantity": float(line.quantity),
                    "unit": line.unit or (item.unit if item else ""),
                    "stock_available": stock_available,
                    "enough_stock": enough_stock,
                    "inventory_item_id": (
                        str(line.inventory_item_id) if line.inventory_item_id else None
                    ),
                })
                if not enough_stock:
                    warnings.append(
                        f"Stock insuficiente de '{item_name}': "
                        f"disponible {stock_available}, necesario {float(line.quantity)}"
                    )
                total_cost += line.unit_cost * line.quantity

        return WorkOrderPreview(
            budget_id=budget_id,
            budget_number=budget.budget_number,
            customer_name=budget.customer.name if budget.customer else None,
            tasks_to_create=tasks_to_create,
            materials_to_reserve=materials_to_reserve,
            warnings=warnings,
            total_estimated_cost=total_cost,
        )

    async def accept_and_create_work_order(self, budget_id: uuid.UUID) -> dict:
        """
        STEP 2: accepts the budget, creates WorkOrder + Tasks + TaskMaterials.
        The user must have confirmed the preview first.
        """
        from app.services.work_order import WorkOrderService

        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede aceptar un presupuesto en estado enviado",
            )

        # Mark as accepted and flush — the commit is done inside create_from_budget
        await self._repo.update(budget, {"status": BudgetStatus.ACCEPTED})
        await self._session.flush()
        logger.info("Budget accepted id=%s", budget_id)

        work_order_service = WorkOrderService(self._session)
        work_order = await work_order_service.create_from_budget(budget_id)

        return {
            "budget_id": str(budget_id),
            "status": "accepted",
            "work_order_id": str(work_order.id),
            "work_order_number": work_order.work_order_number,
            "message": "Presupuesto aceptado y obra creada correctamente",
        }

    # ── PDF generation ────────────────────────────────────────────────────────

    async def generate_pdf(self, budget_id: uuid.UUID) -> bytes:
        """
        Generates the budget PDF using WeasyPrint + Jinja2.
        Saves the file to uploads/budgets/{budget_id}/ and updates budget.pdf_path.
        Returns the PDF bytes for the HTTP response.
        """
        from weasyprint import HTML

        from app.utils.pdf_renderer import render_budget_pdf_html

        budget = await self._repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )

        company = await self._company_repo.get()
        totals = self._calculate_totals(budget)

        # Build public lines (no unit_cost / margin)
        public_lines = [self._build_line_public_response(line) for line in budget.lines]

        # Resolve client address
        address = None
        if budget.customer and budget.customer.addresses:
            primary = next(
                (a for a in budget.customer.addresses if a.is_default),
                budget.customer.addresses[0],
            )
            address = f"{primary.street}, {primary.postal_code} {primary.city}"

        html_content = render_budget_pdf_html(
            budget=budget,
            company=company,
            totals=totals,
            customer=budget.customer,
            address=address,
            lines=public_lines,
        )

        pdf_bytes = HTML(string=html_content).write_pdf()

        upload_dir = Path(settings.UPLOAD_DIR) / "budgets" / str(budget_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = upload_dir / f"presupuesto_{budget.budget_number}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        await self._repo.update(budget, {"pdf_path": str(pdf_path)})
        await self._session.commit()

        logger.info("PDF generated for budget id=%s path=%s", budget_id, pdf_path)
        return pdf_bytes

    # ── Lines management ──────────────────────────────────────────────────────

    async def add_line(
        self, budget_id: uuid.UUID, data: BudgetLineCreate
    ) -> BudgetLineInternalResponse:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden añadir líneas a presupuestos en borrador",
            )
        line = await self._create_line(budget_id, data, sort_order=data.sort_order)
        await self._session.commit()
        await self._session.refresh(line)
        if line.inventory_item_id:
            line.inventory_item = await self._item_repo.get_by_id(line.inventory_item_id)
        return self._build_line_response(line)

    async def update_line(
        self,
        budget_id: uuid.UUID,
        line_id: uuid.UUID,
        data,
    ) -> BudgetLineInternalResponse:
        line = await self._line_repo.get_by_id(line_id)
        if not line or line.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Línea no encontrada en este presupuesto",
            )
        budget = await self._repo.get_by_id(budget_id)
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden editar líneas de presupuestos en borrador",
            )
        await self._line_repo.update(line, data.model_dump(exclude_none=True))
        await self._session.commit()
        await self._session.refresh(line)
        if line.inventory_item_id:
            line.inventory_item = await self._item_repo.get_by_id(line.inventory_item_id)
        return self._build_line_response(line)

    async def delete_budget(self, budget_id: uuid.UUID) -> None:
        """Delete a budget. Only allowed for draft or rejected budgets."""
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REJECTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar presupuestos en borrador o rechazados",
            )
        await self._repo.delete(budget)
        await self._session.commit()
        logger.info("Budget deleted id=%s number=%s", budget.id, budget.budget_number)

    async def delete_line(self, budget_id: uuid.UUID, line_id: uuid.UUID) -> None:
        line = await self._line_repo.get_by_id(line_id)
        if not line or line.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Línea no encontrada en este presupuesto",
            )
        budget = await self._repo.get_by_id(budget_id)
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar líneas de presupuestos en borrador",
            )
        await self._line_repo.delete(line)
        await self._session.commit()

    async def reorder_lines(
        self, budget_id: uuid.UUID, data: ReorderLinesRequest
    ) -> BudgetResponse:
        budget = await self._repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden reordenar líneas de presupuestos en borrador",
            )
        for i, line_id in enumerate(data.line_ids):
            await self._session.execute(
                update(BudgetLine)
                .where(BudgetLine.id == line_id)
                .where(BudgetLine.budget_id == budget_id)
                .values(sort_order=i)
            )
        await self._session.commit()
        return await self.get_budget(budget_id)

    # ── Company settings ──────────────────────────────────────────────────────

    async def get_company_settings(self):
        return await self._company_repo.get()

    async def update_company_settings(self, data):
        updated = await self._company_repo.update(data.model_dump(exclude_none=True))
        await self._session.commit()
        return updated

    async def upload_company_logo(self, file: UploadFile) -> str:
        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        upload_dir = Path(settings.UPLOAD_DIR) / "company"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"logo_{file.filename}"
        file_path.write_bytes(content)
        await self._company_repo.update({"logo_path": str(file_path)})
        await self._session.commit()
        return str(file_path)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _calculate_totals(self, budget: Budget) -> BudgetTotals:
        """
        Calculates all budget totals.
        NEVER persist these values — always calculate at runtime.
        """
        subtotal = Decimal("0.0")
        total_cost = Decimal("0.0")

        for line in budget.lines:
            line_subtotal = line.quantity * line.unit_price
            if line.line_discount_pct > 0:
                line_subtotal *= 1 - line.line_discount_pct / 100
            subtotal += line_subtotal
            total_cost += line.quantity * line.unit_cost

        discount_amount = subtotal * (budget.discount_pct / 100)
        taxable_base = subtotal - discount_amount
        tax_amount = taxable_base * (budget.tax_rate / 100)
        total = taxable_base + tax_amount
        gross_margin = total - total_cost
        gross_margin_pct = (
            (gross_margin / total * 100) if total > 0 else Decimal("0.0")
        )

        if gross_margin_pct < 15:
            margin_status = "red"
        elif gross_margin_pct < 25:
            margin_status = "amber"
        else:
            margin_status = "green"

        return BudgetTotals(
            subtotal_before_discount=subtotal.quantize(Decimal("0.01")),
            discount_amount=discount_amount.quantize(Decimal("0.01")),
            taxable_base=taxable_base.quantize(Decimal("0.01")),
            tax_amount=tax_amount.quantize(Decimal("0.01")),
            total=total.quantize(Decimal("0.01")),
            total_cost=total_cost.quantize(Decimal("0.01")),
            gross_margin=gross_margin.quantize(Decimal("0.01")),
            gross_margin_pct=gross_margin_pct.quantize(Decimal("0.01")),
            margin_status=margin_status,
        )

    def _get_effective_status(self, budget: Budget) -> str:
        """Returns 'expired' if sent and valid_until < today."""
        if budget.status == BudgetStatus.SENT and budget.valid_until < date.today():
            return "expired"
        return budget.status.value

    async def _create_line(
        self, budget_id: uuid.UUID, data: BudgetLineCreate, sort_order: int
    ) -> BudgetLine:
        """
        Creates a budget line.
        For material lines with inventory_item_id, auto-fills unit and unit_cost
        from the inventory item if not explicitly provided.
        """
        line_data = data.model_dump()
        line_data["sort_order"] = sort_order

        if data.inventory_item_id and data.line_type == "material":
            item = await self._item_repo.get_by_id(data.inventory_item_id)
            if item:
                if not data.unit:
                    line_data["unit"] = item.unit
                if data.unit_cost == Decimal("0.0"):
                    line_data["unit_cost"] = item.unit_cost_avg or item.unit_cost

        line = BudgetLine(budget_id=budget_id, **line_data)
        return await self._line_repo.create(line)

    def _lines_from_visit(self, visit) -> list[BudgetLineCreate]:
        """
        Converts site visit materials into budget lines.
        - SiteVisitMaterial → BudgetLineCreate(type=material)
        - If visit.estimated_hours → BudgetLineCreate(type=labor)
        """
        lines: list[BudgetLineCreate] = []

        if visit.estimated_hours:
            lines.append(
                BudgetLineCreate(
                    line_type="labor",
                    description="Mano de obra",
                    quantity=visit.estimated_hours,
                    unit="h",
                    unit_price=Decimal("0.0"),
                    unit_cost=Decimal("0.0"),
                    sort_order=0,
                )
            )

        for i, mat in enumerate(visit.materials, start=len(lines)):
            item = mat.inventory_item
            lines.append(
                BudgetLineCreate(
                    line_type="material",
                    description=item.name if item else (mat.description or "Material"),
                    inventory_item_id=mat.inventory_item_id,
                    quantity=mat.estimated_qty,
                    unit=mat.unit or (item.unit if item else None),
                    unit_price=item.unit_price if item else (mat.unit_cost or Decimal("0.0")),
                    unit_cost=(
                        item.unit_cost_avg if item else (mat.unit_cost or Decimal("0.0"))
                    ),
                    sort_order=i,
                )
            )

        return lines

    def _build_line_public_response(self, line: BudgetLine) -> BudgetLinePublicResponse:
        """Public response without cost/margin — safe for PDF and client views."""
        subtotal = line.quantity * line.unit_price
        if line.line_discount_pct > 0:
            subtotal *= 1 - line.line_discount_pct / 100
        return BudgetLinePublicResponse(
            id=line.id,
            line_type=line.line_type.value,
            sort_order=line.sort_order,
            description=line.description,
            inventory_item_id=line.inventory_item_id,
            inventory_item_name=(
                line.inventory_item.name if line.inventory_item else None
            ),
            quantity=line.quantity,
            unit=line.unit,
            unit_price=line.unit_price,
            line_discount_pct=line.line_discount_pct,
            subtotal=subtotal.quantize(Decimal("0.01")),
        )

    def _build_line_response(self, line: BudgetLine) -> BudgetLineInternalResponse:
        subtotal = line.quantity * line.unit_price
        if line.line_discount_pct > 0:
            subtotal *= 1 - line.line_discount_pct / 100
        margin_pct = (
            (line.unit_price - line.unit_cost) / line.unit_price * 100
            if line.unit_price > 0
            else Decimal("0.0")
        )
        return BudgetLineInternalResponse(
            id=line.id,
            line_type=line.line_type.value,
            sort_order=line.sort_order,
            description=line.description,
            inventory_item_id=line.inventory_item_id,
            inventory_item_name=(
                line.inventory_item.name if line.inventory_item else None
            ),
            quantity=line.quantity,
            unit=line.unit,
            unit_price=line.unit_price,
            line_discount_pct=line.line_discount_pct,
            subtotal=subtotal.quantize(Decimal("0.01")),
            unit_cost=line.unit_cost,
            margin_pct=margin_pct.quantize(Decimal("0.01")),
            margin_amount=(
                (line.unit_price - line.unit_cost) * line.quantity
            ).quantize(Decimal("0.01")),
        )

    def _build_version_info(self, budget: Budget) -> BudgetVersionInfo:
        totals = self._calculate_totals(budget)
        return BudgetVersionInfo(
            id=budget.id,
            version=budget.version,
            budget_number=budget.budget_number,
            status=budget.status.value,
            effective_status=self._get_effective_status(budget),
            issue_date=budget.issue_date,
            total=totals.total,
            is_latest_version=budget.is_latest_version,
        )

    def _build_summary(self, budget: Budget) -> BudgetSummary:
        totals = self._calculate_totals(budget)
        return BudgetSummary(
            id=budget.id,
            budget_number=budget.budget_number,
            version=budget.version,
            is_latest_version=budget.is_latest_version,
            customer_id=budget.customer_id,
            customer_name=budget.customer.name if budget.customer else None,
            site_visit_id=budget.site_visit_id,
            status=budget.status.value,
            effective_status=self._get_effective_status(budget),
            issue_date=budget.issue_date,
            valid_until=budget.valid_until,
            discount_pct=budget.discount_pct,
            tax_rate=budget.tax_rate,
            total=totals.total,
            gross_margin_pct=totals.gross_margin_pct,
            margin_status=totals.margin_status,
            lines_count=len(budget.lines),
            has_pdf=budget.pdf_path is not None,
            created_at=budget.created_at,
        )

    def _build_response(self, budget: Budget) -> BudgetResponse:
        totals = self._calculate_totals(budget)
        summary = self._build_summary(budget)
        return BudgetResponse(
            **summary.model_dump(),
            parent_budget_id=budget.parent_budget_id,
            work_order_id=budget.work_order_id,
            notes=budget.notes,
            client_notes=budget.client_notes,
            lines=[self._build_line_response(line) for line in budget.lines],
            totals=totals,
            versions=[],
            updated_at=budget.updated_at,
        )
