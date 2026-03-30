"""Router for the Budget module, including Company Settings."""

import uuid
from datetime import date

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.budget import (
    BudgetCreate,
    BudgetFromVisitRequest,
    BudgetLineCreate,
    BudgetLineInternalResponse,
    BudgetLineUpdate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
    BudgetVersionInfo,
    ReorderLinesRequest,
    WorkOrderPreview,
)
from app.schemas.company_settings import CompanySettingsResponse, CompanySettingsUpdate
from app.services.budget import BudgetService

router = APIRouter(tags=["Presupuestos"])


# ── Company settings ───────────────────────────────────────────────────────────

@router.get("/company-settings", response_model=CompanySettingsResponse)
async def get_company_settings(db: DbSession, _: CurrentUser):
    return await BudgetService(db).get_company_settings()


@router.patch("/company-settings", response_model=CompanySettingsResponse)
async def update_company_settings(
    data: CompanySettingsUpdate, db: DbSession, _: CurrentUser
):
    return await BudgetService(db).update_company_settings(data)


@router.post("/company-settings/logo")
async def upload_company_logo(
    db: DbSession, _: CurrentUser, file: UploadFile = File(...)
):
    logo_path = await BudgetService(db).upload_company_logo(file)
    return {"logo_path": logo_path}


# ── Budgets ────────────────────────────────────────────────────────────────────

@router.get("/budgets", response_model=BudgetListResponse)
async def list_budgets(
    db: DbSession,
    _: CurrentUser,
    q: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    latest_only: bool = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    return await BudgetService(db).list_budgets(
        q=q,
        customer_id=customer_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        latest_only=latest_only,
        skip=skip,
        limit=limit,
    )


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(data: BudgetCreate, db: DbSession, _: CurrentUser):
    return await BudgetService(db).create_budget(data)


@router.post(
    "/budgets/from-visit",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_budget_from_visit(
    data: BudgetFromVisitRequest, db: DbSession, _: CurrentUser
):
    return await BudgetService(db).create_budget_from_visit(data)


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).get_budget(budget_id)


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID, data: BudgetUpdate, db: DbSession, _: CurrentUser
):
    return await BudgetService(db).update_budget(budget_id, data)


@router.get(
    "/budgets/{budget_id}/versions", response_model=list[BudgetVersionInfo]
)
async def get_budget_versions(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).get_budget_versions(budget_id)


# ── Lifecycle ──────────────────────────────────────────────────────────────────

@router.post("/budgets/{budget_id}/send", response_model=BudgetResponse)
async def send_budget(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).send_budget(budget_id)


@router.post("/budgets/{budget_id}/reject", response_model=BudgetResponse)
async def reject_budget(
    budget_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    notes: str | None = Query(default=None),
):
    return await BudgetService(db).reject_budget(budget_id, notes)


@router.post("/budgets/{budget_id}/new-version", response_model=BudgetResponse)
async def create_new_version(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).create_new_version(budget_id)


@router.get(
    "/budgets/{budget_id}/work-order-preview", response_model=WorkOrderPreview
)
async def get_work_order_preview(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).get_work_order_preview(budget_id)


@router.post("/budgets/{budget_id}/accept")
async def accept_budget(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    return await BudgetService(db).accept_and_create_work_order(budget_id)


# ── PDF ────────────────────────────────────────────────────────────────────────

@router.post("/budgets/{budget_id}/generate-pdf")
async def generate_pdf(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    pdf_bytes = await BudgetService(db).generate_pdf(budget_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=presupuesto_{budget_id}.pdf"
        },
    )


@router.get("/budgets/{budget_id}/pdf")
async def download_pdf(budget_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Download existing PDF. Generates it on demand if not yet created."""
    # Always regenerate to ensure it's up to date; caching is a future concern
    pdf_bytes = await BudgetService(db).generate_pdf(budget_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=presupuesto_{budget_id}.pdf"
        },
    )


# ── Lines ──────────────────────────────────────────────────────────────────────

@router.post(
    "/budgets/{budget_id}/lines",
    response_model=BudgetLineInternalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_line(
    budget_id: uuid.UUID, data: BudgetLineCreate, db: DbSession, _: CurrentUser
):
    return await BudgetService(db).add_line(budget_id, data)


@router.patch(
    "/budgets/{budget_id}/lines/{line_id}", response_model=BudgetLineInternalResponse
)
async def update_line(
    budget_id: uuid.UUID,
    line_id: uuid.UUID,
    data: BudgetLineUpdate,
    db: DbSession,
    _: CurrentUser,
):
    return await BudgetService(db).update_line(budget_id, line_id, data)


@router.delete(
    "/budgets/{budget_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_line(
    budget_id: uuid.UUID, line_id: uuid.UUID, db: DbSession, _: CurrentUser
):
    await BudgetService(db).delete_line(budget_id, line_id)


@router.put("/budgets/{budget_id}/lines/reorder", response_model=BudgetResponse)
async def reorder_lines(
    budget_id: uuid.UUID, data: ReorderLinesRequest, db: DbSession, _: CurrentUser
):
    return await BudgetService(db).reorder_lines(budget_id, data)
