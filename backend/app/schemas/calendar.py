"""Schemas for the Calendar module."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    start_datetime: str = Field(..., description="ISO 8601 datetime or date string")
    end_datetime: str | None = Field(default=None, description="ISO 8601 datetime or date string")
    all_day: bool = False
    color: str = Field(default="#8b5cf6", max_length=20)


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    all_day: bool | None = None
    color: str | None = Field(default=None, max_length=20)


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    start_datetime: str
    end_datetime: str | None
    all_day: bool
    color: str
    created_by: UUID | None


# Unified event shape returned by the aggregation endpoint
class CalendarAggregatedEvent(BaseModel):
    id: str
    title: str
    description: str | None = None
    start: str  # ISO 8601
    end: str | None = None
    all_day: bool = False
    color: str
    event_type: str  # site_visit | budget | work_order | custom
    entity_id: str | None = None
    url: str | None = None
