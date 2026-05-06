"""Router for reusable budget templates."""

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.budget_template import (
    ApplyTemplateRequest,
    BudgetTemplateCreate,
    BudgetTemplateListResponse,
    BudgetTemplateResponse,
    BudgetTemplateUpdate,
)
from app.services.budget_template import BudgetTemplateService

router = APIRouter(tags=["Plantillas de presupuesto"])


@router.get("/budget-templates", response_model=BudgetTemplateListResponse)
async def list_templates(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    q: str | None = Query(default=None),
):
    return await BudgetTemplateService(db, tenant_id).list_templates(q=q)


@router.post(
    "/budget-templates",
    response_model=BudgetTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: BudgetTemplateCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await BudgetTemplateService(db, tenant_id).create_template(data)


@router.get("/budget-templates/{template_id}", response_model=BudgetTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await BudgetTemplateService(db, tenant_id).get_template(template_id)


@router.patch(
    "/budget-templates/{template_id}", response_model=BudgetTemplateResponse
)
async def update_template(
    template_id: uuid.UUID,
    data: BudgetTemplateUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await BudgetTemplateService(db, tenant_id).update_template(
        template_id, data
    )


@router.delete(
    "/budget-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_template(
    template_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    await BudgetTemplateService(db, tenant_id).delete_template(template_id)


@router.post(
    "/budgets/{budget_id}/apply-template",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def apply_template_to_budget(
    budget_id: uuid.UUID,
    data: ApplyTemplateRequest,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    await BudgetTemplateService(db, tenant_id).apply_to_budget(
        template_id=data.template_id,
        budget_id=budget_id,
        mode=data.mode,
    )


@router.post(
    "/budgets/{budget_id}/save-as-template",
    response_model=BudgetTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_budget_as_template(
    budget_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    name: str = Query(..., min_length=1, max_length=255),
    description: str | None = Query(default=None),
):
    return await BudgetTemplateService(db, tenant_id).save_budget_as_template(
        budget_id=budget_id,
        name=name,
        description=description,
    )
