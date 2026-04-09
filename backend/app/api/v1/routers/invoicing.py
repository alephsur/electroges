"""Invoicing API router."""

import uuid

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceFilters,
    InvoiceFromWorkOrderRequest,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentCreate,
    PaymentReminderResponse,
    RectificationRequest,
    ReorderLinesRequest,
    InvoiceLineCreate,
    InvoiceLineUpdate,
)
from app.services.invoice import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    q: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    work_order_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    overdue_only: bool = Query(default=False),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    from datetime import date as dt_date

    filters = InvoiceFilters(
        q=q,
        customer_id=customer_id,
        work_order_id=work_order_id,
        status=status,
        overdue_only=overdue_only,
        date_from=dt_date.fromisoformat(date_from) if date_from else None,
        date_to=dt_date.fromisoformat(date_to) if date_to else None,
        skip=skip,
        limit=limit,
    )
    svc = InvoiceService(db, tenant_id)
    return await svc.list_invoices(filters)


@router.post(
    "", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED
)
async def create_invoice(
    data: InvoiceCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.create_invoice(data)


@router.post(
    "/from-work-order",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_from_work_order(
    data: InvoiceFromWorkOrderRequest,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.create_from_work_order(data)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.get_invoice(invoice_id)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.update_invoice(invoice_id, data)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.send_invoice(invoice_id)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    reason: str,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.cancel_invoice(invoice_id, reason)


@router.post("/{invoice_id}/rectify", response_model=InvoiceResponse)
async def create_rectification(
    invoice_id: uuid.UUID,
    data: RectificationRequest,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.create_rectification(invoice_id, data)


# ── PDF ───────────────────────────────────────────────────────────────────────

@router.post("/{invoice_id}/generate-pdf")
async def generate_pdf(
    invoice_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    pdf_bytes = await svc.generate_pdf(invoice_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=factura.pdf"
        },
    )


@router.get("/{invoice_id}/pdf")
async def download_pdf(
    invoice_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    from pathlib import Path

    from fastapi import HTTPException

    svc = InvoiceService(db, tenant_id)
    invoice = await svc.get_invoice(invoice_id)
    if not invoice.has_pdf or not invoice.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF no encontrado. Genera el PDF primero.",
        )
    pdf_path = Path(invoice.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo PDF no encontrado en el servidor",
        )
    return StreamingResponse(
        content=open(pdf_path, "rb"),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=factura_{invoice.invoice_number}.pdf"
            )
        },
    )


# ── Reminder ──────────────────────────────────────────────────────────────────

@router.get(
    "/{invoice_id}/reminder", response_model=PaymentReminderResponse
)
async def get_payment_reminder(
    invoice_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.get_payment_reminder(invoice_id)


# ── Lines ─────────────────────────────────────────────────────────────────────

@router.post(
    "/{invoice_id}/lines",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_line(
    invoice_id: uuid.UUID,
    data: InvoiceLineCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.add_line(invoice_id, data)


@router.patch(
    "/{invoice_id}/lines/{line_id}", response_model=InvoiceResponse
)
async def update_line(
    invoice_id: uuid.UUID,
    line_id: uuid.UUID,
    data: InvoiceLineUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.update_line(invoice_id, line_id, data)


@router.delete(
    "/{invoice_id}/lines/{line_id}", response_model=InvoiceResponse
)
async def delete_line(
    invoice_id: uuid.UUID,
    line_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.delete_line(invoice_id, line_id)


@router.put(
    "/{invoice_id}/lines/reorder", response_model=InvoiceResponse
)
async def reorder_lines(
    invoice_id: uuid.UUID,
    data: ReorderLinesRequest,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.reorder_lines(invoice_id, data)


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post(
    "/{invoice_id}/payments",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_payment(
    invoice_id: uuid.UUID,
    data: PaymentCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.register_payment(invoice_id, data)


@router.delete(
    "/{invoice_id}/payments/{payment_id}", response_model=InvoiceResponse
)
async def delete_payment(
    invoice_id: uuid.UUID,
    payment_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    svc = InvoiceService(db, tenant_id)
    return await svc.delete_payment(invoice_id, payment_id)
