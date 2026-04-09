"""Repository for SiteVisit and related models."""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.site_visit import (
    SiteVisit,
    SiteVisitDocument,
    SiteVisitMaterial,
    SiteVisitPhoto,
)
from app.repositories.base import BaseRepository


class SiteVisitRepository(BaseRepository[SiteVisit]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(SiteVisit, session, tenant_id)

    async def search(
        self,
        query: str | None,
        customer_id: uuid.UUID | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        skip: int,
        limit: int,
    ) -> tuple[list[SiteVisit], int]:
        """Search with filters. Eager-loads customer, materials, photos, documents for summary."""
        from app.models.customer import Customer

        stmt = select(SiteVisit).options(
            selectinload(SiteVisit.customer),
            selectinload(SiteVisit.materials),
            selectinload(SiteVisit.photos),
            selectinload(SiteVisit.documents),
        )
        count_stmt = select(func.count()).select_from(SiteVisit)

        if self.tenant_id is not None:
            stmt = stmt.where(SiteVisit.tenant_id == self.tenant_id)
            count_stmt = count_stmt.where(SiteVisit.tenant_id == self.tenant_id)

        if customer_id is not None:
            stmt = stmt.where(SiteVisit.customer_id == customer_id)
            count_stmt = count_stmt.where(SiteVisit.customer_id == customer_id)

        if status is not None:
            stmt = stmt.where(SiteVisit.status == status)
            count_stmt = count_stmt.where(SiteVisit.status == status)

        if date_from is not None:
            stmt = stmt.where(SiteVisit.visit_date >= date_from)
            count_stmt = count_stmt.where(SiteVisit.visit_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(SiteVisit.visit_date <= date_to)
            count_stmt = count_stmt.where(SiteVisit.visit_date <= date_to)

        if query:
            pattern = f"%{query}%"
            stmt = stmt.outerjoin(Customer, SiteVisit.customer_id == Customer.id)
            count_stmt = count_stmt.outerjoin(Customer, SiteVisit.customer_id == Customer.id)
            search_filter = or_(
                SiteVisit.contact_name.ilike(pattern),
                SiteVisit.address_text.ilike(pattern),
                Customer.name.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(SiteVisit.created_at.desc()).offset(skip).limit(limit)

        rows = await self.session.execute(stmt)
        total_result = await self.session.execute(count_stmt)
        return list(rows.scalars().all()), total_result.scalar_one()

    async def get_with_full_detail(self, visit_id: uuid.UUID) -> SiteVisit | None:
        """Eager-loads all related objects for the detail view."""
        stmt = (
            select(SiteVisit)
            .options(
                selectinload(SiteVisit.customer),
                selectinload(SiteVisit.customer_address),
                selectinload(SiteVisit.materials).selectinload(SiteVisitMaterial.inventory_item),
                selectinload(SiteVisit.photos),
                selectinload(SiteVisit.documents),
            )
            .where(SiteVisit.id == visit_id)
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_customer(
        self, customer_id: uuid.UUID, skip: int, limit: int
    ) -> list[SiteVisit]:
        """For the customer timeline."""
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.customer_id == customer_id)
            .order_by(SiteVisit.visit_date.desc())
            .offset(skip)
            .limit(limit)
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reorder_photos(
        self, visit_id: uuid.UUID, photo_ids: list[uuid.UUID]
    ) -> None:
        """Updates sort_order for each photo using direct SQL UPDATE per item."""
        for i, photo_id in enumerate(photo_ids):
            await self.session.execute(
                update(SiteVisitPhoto)
                .where(SiteVisitPhoto.id == photo_id)
                .where(SiteVisitPhoto.site_visit_id == visit_id)
                .values(sort_order=i)
            )


class SiteVisitMaterialRepository(BaseRepository[SiteVisitMaterial]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(SiteVisitMaterial, session, tenant_id)


class SiteVisitPhotoRepository(BaseRepository[SiteVisitPhoto]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(SiteVisitPhoto, session, tenant_id)

    async def get_by_visit(self, visit_id: uuid.UUID) -> list[SiteVisitPhoto]:
        result = await self.session.execute(
            select(SiteVisitPhoto)
            .where(SiteVisitPhoto.site_visit_id == visit_id)
            .order_by(SiteVisitPhoto.sort_order)
        )
        return list(result.scalars().all())


class SiteVisitDocumentRepository(BaseRepository[SiteVisitDocument]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(SiteVisitDocument, session, tenant_id)
