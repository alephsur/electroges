"""Calendar router: aggregated events + custom event CRUD."""

import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.calendar import (
    CalendarAggregatedEvent,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
)
from app.services.calendar import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendario"])


@router.get("/events", response_model=list[CalendarAggregatedEvent])
async def get_aggregated_events(
    db: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId,
    date_from: date = Query(..., description="Start of the range (inclusive)"),
    date_to: date = Query(..., description="End of the range (inclusive)"),
):
    return await CalendarService(db, tenant_id).get_aggregated_events(date_from, date_to)


@router.get("/custom-events", response_model=list[CalendarEventResponse])
async def list_custom_events(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await CalendarService(db, tenant_id).list_custom_events()


@router.post("/custom-events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_event(
    data: CalendarEventCreate,
    db: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await CalendarService(db, tenant_id).create_event(data, current_user.id)


@router.patch("/custom-events/{event_id}", response_model=CalendarEventResponse)
async def update_custom_event(
    event_id: uuid.UUID,
    data: CalendarEventUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await CalendarService(db, tenant_id).update_event(event_id, data)


@router.delete("/custom-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_event(
    event_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    await CalendarService(db, tenant_id).delete_event(event_id)
