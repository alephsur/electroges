"""Service layer for the Calendar module."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.repositories.calendar import CalendarEventRepository
from app.schemas.calendar import (
    CalendarAggregatedEvent,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
)

# Color mapping per entity type
_COLORS = {
    "site_visit": "#3b82f6",   # blue
    "budget": "#10b981",       # green
    "work_order": "#f97316",   # orange
    "custom": "#8b5cf6",       # purple
}

_STATUS_LABELS = {
    # SiteVisit
    "scheduled": "Programada",
    "in_progress": "En curso",
    "completed": "Completada",
    "cancelled": "Cancelada",
    "no_show": "No presentado",
    # Budget
    "draft": "Borrador",
    "sent": "Enviado",
    "accepted": "Aceptado",
    "rejected": "Rechazado",
    "expired": "Expirado",
    # WorkOrder
    "active": "Activa",
    "pending_closure": "Pend. cierre",
    "closed": "Cerrada",
}


class CalendarService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.repo = CalendarEventRepository(session, tenant_id)
        self.tenant_id = tenant_id

    # ── Aggregated events ─────────────────────────────────────────────────────

    async def get_aggregated_events(
        self, date_from: date, date_to: date
    ) -> list[CalendarAggregatedEvent]:
        events: list[CalendarAggregatedEvent] = []

        # Site visits
        for sv in await self.repo.get_site_visits_in_range(date_from, date_to):
            customer_name = sv.customer.name if sv.customer else "Sin cliente"
            status_label = _STATUS_LABELS.get(sv.status.value if hasattr(sv.status, 'value') else sv.status, sv.status)
            address_text = sv.address_text or (sv.customer_address.street if sv.customer_address else "") or ""
            events.append(CalendarAggregatedEvent(
                id=f"sv-{sv.id}",
                title=f"Visita: {customer_name}",
                description=f"{status_label} · {address_text}".rstrip(" ·"),
                start=sv.visit_date.isoformat(),
                end=None,
                all_day=False,
                color=_COLORS["site_visit"],
                event_type="site_visit",
                entity_id=str(sv.id),
                url=f"/visitas/{sv.id}",
            ))

        # Budgets — one point-in-time event per budget on its issue_date only
        for b in await self.repo.get_budgets_in_range(date_from, date_to):
            customer_name = b.customer.name if b.customer else "Sin cliente"
            status_label = _STATUS_LABELS.get(b.status.value if hasattr(b.status, 'value') else b.status, b.status)
            events.append(CalendarAggregatedEvent(
                id=f"b-{b.id}",
                title=f"Pres. {b.budget_number}: {customer_name}",
                description=f"{status_label}",
                start=b.issue_date.isoformat(),
                end=None,  # point event — appears only on issue_date
                all_day=True,
                color=_COLORS["budget"],
                event_type="budget",
                entity_id=str(b.id),
                url=f"/presupuestos/{b.id}",
            ))

        # Work orders — span from start_date to end_date; open ones extend to today
        today = date.today()
        for wo in await self.repo.get_work_orders_in_range(date_from, date_to):
            customer_name = wo.customer.name if wo.customer else "Sin cliente"
            wo_status = wo.status.value if hasattr(wo.status, 'value') else wo.status
            status_label = _STATUS_LABELS.get(wo_status, wo_status)
            wo_start = wo.start_date if wo.start_date else wo.created_at.date()
            if wo.end_date:
                wo_end = wo.end_date
            elif wo_status in ("closed", "cancelled"):
                # Use updated_at as proxy for closure date when end_date not explicitly set
                wo_end = wo.updated_at.date()
            else:
                # Still open — extend to today so it fills the calendar up to now
                wo_end = today
            events.append(CalendarAggregatedEvent(
                id=f"wo-{wo.id}",
                title=f"Obra {wo.work_order_number}: {customer_name}",
                description=f"{status_label} · {wo.address or ''}",
                start=wo_start.isoformat(),
                end=wo_end.isoformat(),
                all_day=True,
                color=_COLORS["work_order"],
                event_type="work_order",
                entity_id=str(wo.id),
                url=f"/obras/{wo.id}",
            ))

        # Custom events
        for ce in await self.repo.get_custom_events_in_range(date_from, date_to):
            events.append(CalendarAggregatedEvent(
                id=f"ce-{ce.id}",
                title=ce.title,
                description=ce.description,
                start=ce.start_datetime,
                end=ce.end_datetime,
                all_day=ce.all_day,
                color=ce.color,
                event_type="custom",
                entity_id=str(ce.id),
                url=None,
            ))

        return events

    # ── Custom event CRUD ─────────────────────────────────────────────────────

    async def list_custom_events(self) -> list[CalendarEventResponse]:
        events = await self.repo.list_events()
        return [CalendarEventResponse.model_validate(e) for e in events]

    async def create_event(
        self, data: CalendarEventCreate, user_id: uuid.UUID
    ) -> CalendarEventResponse:
        event = CalendarEvent(
            tenant_id=self.tenant_id,
            title=data.title,
            description=data.description,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            all_day=data.all_day,
            color=data.color,
            created_by=user_id,
        )
        event = await self.repo.create(event)
        await self.repo.session.commit()
        return CalendarEventResponse.model_validate(event)

    async def update_event(
        self, event_id: uuid.UUID, data: CalendarEventUpdate
    ) -> CalendarEventResponse:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")
        update_data = data.model_dump(exclude_unset=True)
        event = await self.repo.update(event, update_data)
        await self.repo.session.commit()
        return CalendarEventResponse.model_validate(event)

    async def delete_event(self, event_id: uuid.UUID) -> None:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")
        await self.repo.delete(event)
        await self.repo.session.commit()
