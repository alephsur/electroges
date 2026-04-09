"""Repository for CalendarEvent and calendar aggregation queries."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetStatus
from app.models.calendar_event import CalendarEvent
from app.models.site_visit import SiteVisit
from app.models.work_order import WorkOrder
from app.repositories.base import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(CalendarEvent, session, tenant_id)

    async def list_events(self) -> list[CalendarEvent]:
        stmt = select(CalendarEvent)
        if self.tenant_id is not None:
            stmt = stmt.where(CalendarEvent.tenant_id == self.tenant_id)
        stmt = stmt.order_by(CalendarEvent.start_datetime)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Aggregation ───────────────────────────────────────────────────────────

    async def get_site_visits_in_range(
        self, date_from: date, date_to: date
    ) -> list[SiteVisit]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(SiteVisit)
            .options(
                selectinload(SiteVisit.customer),
                selectinload(SiteVisit.customer_address),
            )
            .where(
                SiteVisit.visit_date >= date_from,
                SiteVisit.visit_date <= date_to,
            )
        )
        if self.tenant_id is not None:
            stmt = stmt.where(SiteVisit.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_budgets_in_range(
        self, date_from: date, date_to: date
    ) -> list[Budget]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Budget)
            .options(selectinload(Budget.customer))
            .where(
                Budget.issue_date >= date_from,
                Budget.issue_date <= date_to,
            )
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Budget.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_work_orders_in_range(
        self, date_from: date, date_to: date
    ) -> list[WorkOrder]:
        from sqlalchemy.orm import selectinload

        # Include work orders that overlap with the requested range.
        # A work order overlaps if:
        #   its start (start_date or created_at::date) <= date_to
        #   AND its end (end_date if set, or very far future for open ones) >= date_from
        stmt = (
            select(WorkOrder)
            .options(selectinload(WorkOrder.customer))
            .where(
                WorkOrder.status.not_in(["cancelled"]),
            )
        )
        if self.tenant_id is not None:
            stmt = stmt.where(WorkOrder.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        all_orders = list(result.scalars().all())

        # Filter in Python to handle nullable start_date with created_at fallback
        filtered = []
        for wo in all_orders:
            wo_start: date = wo.start_date if wo.start_date else wo.created_at.date()
            wo_end: date | None = wo.end_date
            # Open work orders extend to "infinity" for display purposes
            if wo_start <= date_to and (wo_end is None or wo_end >= date_from):
                filtered.append(wo)
        return filtered

    async def get_custom_events_in_range(
        self, date_from: date, date_to: date
    ) -> list[CalendarEvent]:
        stmt = select(CalendarEvent)
        if self.tenant_id is not None:
            stmt = stmt.where(CalendarEvent.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        all_events = list(result.scalars().all())

        # Filter in Python (start_datetime is ISO string, compare by prefix)
        date_from_str = date_from.isoformat()
        date_to_str = date_to.isoformat()
        filtered = []
        for ev in all_events:
            ev_start = ev.start_datetime[:10]
            ev_end = ev.end_datetime[:10] if ev.end_datetime else ev_start
            if ev_start <= date_to_str and ev_end >= date_from_str:
                filtered.append(ev)
        return filtered
