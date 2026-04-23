"""Repository for BudgetTemplate and its nested models."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget_template import (
    BudgetTemplate,
    BudgetTemplateLine,
    BudgetTemplateSection,
)
from app.repositories.base import BaseRepository


class BudgetTemplateRepository(BaseRepository[BudgetTemplate]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(BudgetTemplate, session, tenant_id)

    async def list_with_counts(
        self, q: str | None = None
    ) -> list[tuple[BudgetTemplate, int, int]]:
        """Returns tuples of (template, sections_count, lines_count)."""
        stmt = select(BudgetTemplate)
        if self.tenant_id is not None:
            stmt = stmt.where(BudgetTemplate.tenant_id == self.tenant_id)
        if q:
            stmt = stmt.where(BudgetTemplate.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(BudgetTemplate.name.asc())
        stmt = stmt.options(
            selectinload(BudgetTemplate.sections),
            selectinload(BudgetTemplate.lines),
        )
        result = await self.session.execute(stmt)
        return [
            (
                t,
                len(t.sections),
                len(t.lines),
            )
            for t in result.scalars().all()
        ]

    async def get_with_full_detail(
        self, template_id: uuid.UUID
    ) -> BudgetTemplate | None:
        stmt = (
            select(BudgetTemplate)
            .options(
                selectinload(BudgetTemplate.sections),
                selectinload(BudgetTemplate.lines),
            )
            .where(BudgetTemplate.id == template_id)
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def name_exists(
        self, name: str, exclude_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(func.count(BudgetTemplate.id)).where(
            BudgetTemplate.name == name
        )
        if self.tenant_id is not None:
            stmt = stmt.where(BudgetTemplate.tenant_id == self.tenant_id)
        if exclude_id:
            stmt = stmt.where(BudgetTemplate.id != exclude_id)
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0


class BudgetTemplateSectionRepository(BaseRepository[BudgetTemplateSection]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(BudgetTemplateSection, session, tenant_id)


class BudgetTemplateLineRepository(BaseRepository[BudgetTemplateLine]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(BudgetTemplateLine, session, tenant_id)
