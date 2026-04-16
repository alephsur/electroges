"""Service layer for the Dashboard module."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import DashboardSummary, RecentActivityPage


class DashboardService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.repo = DashboardRepository(session, tenant_id)

    async def get_summary(self, date_from: date, date_to: date) -> DashboardSummary:
        return await self.repo.get_summary(date_from, date_to)

    async def get_recent_activity_page(
        self, page: int, page_size: int
    ) -> RecentActivityPage:
        return await self.repo.get_recent_activity_page(page, page_size)
