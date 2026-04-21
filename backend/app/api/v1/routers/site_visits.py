import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.site_visit import (
    SiteVisitCreate,
    SiteVisitDocumentResponse,
    SiteVisitLinkCustomer,
    SiteVisitListResponse,
    SiteVisitMaterialCreate,
    SiteVisitMaterialResponse,
    SiteVisitMaterialUpdate,
    SiteVisitPhotoResponse,
    SiteVisitPhotoUpdate,
    SiteVisitReorderPhotos,
    SiteVisitResponse,
    SiteVisitStatusUpdate,
    SiteVisitUpdate,
)
from app.services.site_visit import SiteVisitService

router = APIRouter(prefix="/site-visits", tags=["Visitas Técnicas"])


# ── Visits ────────────────────────────────────────────────────────────────────

@router.get("", response_model=SiteVisitListResponse)
async def list_visits(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    q: str | None = Query(default=None, description="Search by customer name, address, contact"),
    customer_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    return await SiteVisitService(db, tenant_id).list_visits(
        q=q,
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=SiteVisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(data: SiteVisitCreate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await SiteVisitService(db, tenant_id).create_visit(data)


@router.get("/{visit_id}", response_model=SiteVisitResponse)
async def get_visit(visit_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await SiteVisitService(db, tenant_id).get_visit(visit_id)


@router.patch("/{visit_id}", response_model=SiteVisitResponse)
async def update_visit(
    visit_id: uuid.UUID, data: SiteVisitUpdate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await SiteVisitService(db, tenant_id).update_visit(visit_id, data)


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(
    visit_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    await SiteVisitService(db, tenant_id).delete_visit(visit_id)


@router.patch("/{visit_id}/status", response_model=SiteVisitResponse)
async def update_status(
    visit_id: uuid.UUID, data: SiteVisitStatusUpdate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await SiteVisitService(db, tenant_id).update_status(visit_id, data)


@router.post("/{visit_id}/link-customer", response_model=SiteVisitResponse)
async def link_customer(
    visit_id: uuid.UUID, data: SiteVisitLinkCustomer, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await SiteVisitService(db, tenant_id).link_customer(visit_id, data)


# ── Materials ─────────────────────────────────────────────────────────────────

@router.get("/{visit_id}/materials", response_model=list[SiteVisitMaterialResponse])
async def list_materials(visit_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await SiteVisitService(db, tenant_id).list_materials(visit_id)


@router.post(
    "/{visit_id}/materials",
    response_model=SiteVisitMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_material(
    visit_id: uuid.UUID, data: SiteVisitMaterialCreate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await SiteVisitService(db, tenant_id).add_material(visit_id, data)


@router.patch("/{visit_id}/materials/{material_id}", response_model=SiteVisitMaterialResponse)
async def update_material(
    visit_id: uuid.UUID,
    material_id: uuid.UUID,
    data: SiteVisitMaterialUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await SiteVisitService(db, tenant_id).update_material(visit_id, material_id, data)


@router.delete(
    "/{visit_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_material(
    visit_id: uuid.UUID, material_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    await SiteVisitService(db, tenant_id).delete_material(visit_id, material_id)


# ── Photos ────────────────────────────────────────────────────────────────────

@router.get("/{visit_id}/photos", response_model=list[SiteVisitPhotoResponse])
async def list_photos(visit_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await SiteVisitService(db, tenant_id).list_photos(visit_id)


@router.post(
    "/{visit_id}/photos",
    response_model=SiteVisitPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    visit_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
):
    return await SiteVisitService(db, tenant_id).upload_photo(visit_id, file, caption)


@router.patch("/{visit_id}/photos/{photo_id}", response_model=SiteVisitPhotoResponse)
async def update_photo(
    visit_id: uuid.UUID,
    photo_id: uuid.UUID,
    data: SiteVisitPhotoUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await SiteVisitService(db, tenant_id).update_photo(visit_id, photo_id, data)


@router.delete(
    "/{visit_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_photo(
    visit_id: uuid.UUID, photo_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    await SiteVisitService(db, tenant_id).delete_photo(visit_id, photo_id)


@router.put("/{visit_id}/photos/reorder", response_model=list[SiteVisitPhotoResponse])
async def reorder_photos(
    visit_id: uuid.UUID, data: SiteVisitReorderPhotos, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await SiteVisitService(db, tenant_id).reorder_photos(visit_id, data.photo_ids)


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/{visit_id}/documents", response_model=list[SiteVisitDocumentResponse])
async def list_documents(visit_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await SiteVisitService(db, tenant_id).list_documents(visit_id)


@router.post(
    "/{visit_id}/documents",
    response_model=SiteVisitDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    visit_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    name: str | None = Form(default=None),
):
    return await SiteVisitService(db, tenant_id).upload_document(visit_id, file, document_type, name)


@router.delete(
    "/{visit_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    visit_id: uuid.UUID, doc_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    await SiteVisitService(db, tenant_id).delete_document(visit_id, doc_id)
