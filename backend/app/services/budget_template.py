"""Service layer for reusable budget templates."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetLine, BudgetSection, BudgetStatus
from app.models.budget_template import (
    BudgetTemplate,
    BudgetTemplateLine,
    BudgetTemplateSection,
)
from app.repositories.budget import (
    BudgetLineRepository,
    BudgetRepository,
    BudgetSectionRepository,
)
from app.repositories.budget_template import (
    BudgetTemplateLineRepository,
    BudgetTemplateRepository,
    BudgetTemplateSectionRepository,
)
from app.schemas.budget_template import (
    BudgetTemplateCreate,
    BudgetTemplateLineResponse,
    BudgetTemplateListResponse,
    BudgetTemplateResponse,
    BudgetTemplateSectionResponse,
    BudgetTemplateSummary,
    BudgetTemplateUpdate,
)

logger = logging.getLogger(__name__)


class BudgetTemplateService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id
        self._repo = BudgetTemplateRepository(session, tenant_id)
        self._section_repo = BudgetTemplateSectionRepository(session, tenant_id)
        self._line_repo = BudgetTemplateLineRepository(session, tenant_id)
        self._budget_repo = BudgetRepository(session, tenant_id)
        self._budget_line_repo = BudgetLineRepository(session, tenant_id)
        self._budget_section_repo = BudgetSectionRepository(session, tenant_id)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list_templates(
        self, q: str | None = None
    ) -> BudgetTemplateListResponse:
        rows = await self._repo.list_with_counts(q=q)
        items: list[BudgetTemplateSummary] = []
        for template, sections_count, lines_count in rows:
            total = sum(
                (line.quantity * line.unit_price)
                * (1 - (line.line_discount_pct / 100))
                for line in template.lines
            )
            items.append(
                BudgetTemplateSummary(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    sections_count=sections_count,
                    lines_count=lines_count,
                    estimated_total=float(total),
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                )
            )
        return BudgetTemplateListResponse(items=items, total=len(items))

    async def get_template(self, template_id: uuid.UUID) -> BudgetTemplateResponse:
        template = await self._repo.get_with_full_detail(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada",
            )
        return self._build_response(template)

    async def create_template(
        self, data: BudgetTemplateCreate
    ) -> BudgetTemplateResponse:
        if await self._repo.name_exists(data.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una plantilla con ese nombre",
            )

        template = BudgetTemplate(
            tenant_id=self._tenant_id,
            name=data.name,
            description=data.description,
        )
        template = await self._repo.create(template)

        # Create sections first and map their index in payload -> db id
        index_to_section_id: dict[int, uuid.UUID] = {}
        for idx, sec_data in enumerate(data.sections):
            section = BudgetTemplateSection(
                template_id=template.id,
                name=sec_data.name,
                notes=sec_data.notes,
                sort_order=sec_data.sort_order or idx,
            )
            section = await self._section_repo.create(section)
            index_to_section_id[idx] = section.id

        # Create lines
        for idx, line_data in enumerate(data.lines):
            section_id = None
            if line_data.section_index is not None:
                section_id = index_to_section_id.get(line_data.section_index)
            line = BudgetTemplateLine(
                template_id=template.id,
                section_id=section_id,
                line_type=line_data.line_type,
                sort_order=line_data.sort_order or idx,
                description=line_data.description,
                inventory_item_id=line_data.inventory_item_id,
                quantity=line_data.quantity,
                unit=line_data.unit,
                unit_price=line_data.unit_price,
                unit_cost=line_data.unit_cost,
                line_discount_pct=line_data.line_discount_pct,
            )
            await self._line_repo.create(line)

        await self._session.commit()
        full = await self._repo.get_with_full_detail(template.id)
        return self._build_response(full)

    async def update_template(
        self, template_id: uuid.UUID, data: BudgetTemplateUpdate
    ) -> BudgetTemplateResponse:
        template = await self._repo.get_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada",
            )
        if data.name and data.name != template.name:
            if await self._repo.name_exists(data.name, exclude_id=template.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe una plantilla con ese nombre",
                )
        await self._repo.update(template, data.model_dump(exclude_none=True))
        await self._session.commit()
        full = await self._repo.get_with_full_detail(template.id)
        return self._build_response(full)

    async def delete_template(self, template_id: uuid.UUID) -> None:
        template = await self._repo.get_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada",
            )
        await self._repo.delete(template)
        await self._session.commit()

    # ── Apply template ────────────────────────────────────────────────────────

    async def apply_to_budget(
        self,
        template_id: uuid.UUID,
        budget_id: uuid.UUID,
        mode: str = "append",
    ) -> None:
        """
        Apply a template to an existing draft budget.
        - append: keep existing sections/lines, append template's ones.
        - replace: delete budget's existing sections and lines first.
        """
        template = await self._repo.get_with_full_detail(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada",
            )
        budget = await self._budget_repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if budget.status != BudgetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden aplicar plantillas a presupuestos en borrador",
            )

        if mode == "replace":
            for line in list(budget.lines):
                await self._budget_line_repo.delete(line)
            for section in list(budget.sections):
                await self._budget_section_repo.delete(section)
            await self._session.flush()

        # Sort order offset so appended items go after existing ones
        section_offset = max(
            (s.sort_order for s in budget.sections), default=-1
        ) + 1
        line_offset = max((l.sort_order for l in budget.lines), default=-1) + 1

        # Clone sections and map template.section.id -> new budget.section.id
        template_sections_sorted = sorted(
            template.sections, key=lambda s: s.sort_order
        )
        section_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for idx, src in enumerate(template_sections_sorted):
            new_section = BudgetSection(
                budget_id=budget.id,
                name=src.name,
                notes=src.notes,
                sort_order=section_offset + idx,
            )
            new_section = await self._budget_section_repo.create(new_section)
            section_id_map[src.id] = new_section.id

        # Clone lines
        template_lines_sorted = sorted(template.lines, key=lambda l: l.sort_order)
        for idx, src in enumerate(template_lines_sorted):
            target_section_id = None
            if src.section_id is not None:
                target_section_id = section_id_map.get(src.section_id)
            new_line = BudgetLine(
                budget_id=budget.id,
                section_id=target_section_id,
                line_type=src.line_type,
                sort_order=line_offset + idx,
                description=src.description,
                inventory_item_id=src.inventory_item_id,
                quantity=src.quantity,
                unit=src.unit,
                unit_price=src.unit_price,
                unit_cost=src.unit_cost,
                line_discount_pct=src.line_discount_pct,
            )
            await self._budget_line_repo.create(new_line)

        await self._session.commit()
        logger.info(
            "Applied template %s to budget %s (mode=%s)",
            template_id,
            budget_id,
            mode,
        )

    # ── Save budget as template ───────────────────────────────────────────────

    async def save_budget_as_template(
        self, budget_id: uuid.UUID, name: str, description: str | None = None
    ) -> BudgetTemplateResponse:
        budget = await self._budget_repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presupuesto no encontrado",
            )
        if await self._repo.name_exists(name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una plantilla con ese nombre",
            )
        template = BudgetTemplate(
            tenant_id=self._tenant_id,
            name=name,
            description=description,
        )
        template = await self._repo.create(template)

        # Copy sections
        section_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for src in sorted(budget.sections, key=lambda s: s.sort_order):
            new_section = BudgetTemplateSection(
                template_id=template.id,
                name=src.name,
                notes=src.notes,
                sort_order=src.sort_order,
            )
            new_section = await self._section_repo.create(new_section)
            section_id_map[src.id] = new_section.id

        # Copy lines
        for src in sorted(budget.lines, key=lambda l: l.sort_order):
            target_section_id = None
            if src.section_id is not None:
                target_section_id = section_id_map.get(src.section_id)
            new_line = BudgetTemplateLine(
                template_id=template.id,
                section_id=target_section_id,
                line_type=src.line_type,
                sort_order=src.sort_order,
                description=src.description,
                inventory_item_id=src.inventory_item_id,
                quantity=src.quantity,
                unit=src.unit,
                unit_price=src.unit_price,
                unit_cost=src.unit_cost,
                line_discount_pct=src.line_discount_pct,
            )
            await self._line_repo.create(new_line)

        await self._session.commit()
        full = await self._repo.get_with_full_detail(template.id)
        return self._build_response(full)

    # ── Builders ──────────────────────────────────────────────────────────────

    def _build_response(self, template: BudgetTemplate) -> BudgetTemplateResponse:
        sections = sorted(template.sections, key=lambda s: s.sort_order)
        lines = sorted(template.lines, key=lambda l: l.sort_order)
        total = sum(
            (Decimal(line.quantity) * Decimal(line.unit_price))
            * (1 - (Decimal(line.line_discount_pct) / 100))
            for line in lines
        )
        return BudgetTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            sections_count=len(sections),
            lines_count=len(lines),
            estimated_total=float(total),
            created_at=template.created_at,
            updated_at=template.updated_at,
            sections=[
                BudgetTemplateSectionResponse(
                    id=s.id,
                    template_id=s.template_id,
                    name=s.name,
                    notes=s.notes,
                    sort_order=s.sort_order,
                )
                for s in sections
            ],
            lines=[
                BudgetTemplateLineResponse(
                    id=l.id,
                    template_id=l.template_id,
                    section_id=l.section_id,
                    line_type=l.line_type.value
                    if hasattr(l.line_type, "value")
                    else l.line_type,
                    sort_order=l.sort_order,
                    description=l.description,
                    inventory_item_id=l.inventory_item_id,
                    quantity=float(l.quantity),
                    unit=l.unit,
                    unit_price=float(l.unit_price),
                    unit_cost=float(l.unit_cost),
                    line_discount_pct=float(l.line_discount_pct),
                )
                for l in lines
            ],
        )
