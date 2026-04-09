"""Dashboard API router."""

from datetime import date

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    today = date.today()
    resolved_from = date_from or date(today.year, 1, 1)
    resolved_to = date_to or today

    service = DashboardService(db, tenant_id)
    return await service.get_summary(resolved_from, resolved_to)
