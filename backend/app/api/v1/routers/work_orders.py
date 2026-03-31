"""Work Orders API router."""

import uuid

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.work_order import (
    CertificationCreate,
    CertificationResponse,
    DeliveryNoteCreate,
    DeliveryNoteResponse,
    DeliveryNoteUpdate,
    NewPurchaseOrderForWorkOrder,
    SendDocumentEmail,
    TaskCreate,
    TaskMaterialConsume,
    TaskMaterialCreate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
    WhatsAppLinkResponse,
    WorkOrderCreate,
    WorkOrderKPIs,
    WorkOrderListResponse,
    WorkOrderPurchaseOrderLink,
    WorkOrderResponse,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)
from app.services.work_order import WorkOrderService

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


# ── Work Orders ───────────────────────────────────────────────────────────────

@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    data: WorkOrderCreate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.create_work_order(data)


@router.get("", response_model=WorkOrderListResponse)
async def list_work_orders(
    db: DbSession,
    _: CurrentUser,
    q: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    svc = WorkOrderService(db)
    return await svc.list_work_orders(
        q=q,
        customer_id=customer_id,
        status_filter=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    work_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.get_work_order(work_order_id)


@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(
    work_order_id: uuid.UUID,
    data: WorkOrderUpdate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.update_work_order(work_order_id, data)


@router.patch(
    "/{work_order_id}/status",
    response_model=WorkOrderResponse,
)
async def update_work_order_status(
    work_order_id: uuid.UUID,
    data: WorkOrderStatusUpdate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.update_status(work_order_id, data)


# ── KPIs ──────────────────────────────────────────────────────────────────────

@router.get("/{work_order_id}/kpis", response_model=WorkOrderKPIs)
async def get_work_order_kpis(
    work_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.get_kpis(work_order_id)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.post(
    "/{work_order_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_task(
    work_order_id: uuid.UUID,
    data: TaskCreate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.add_task(work_order_id, data)


@router.patch(
    "/{work_order_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    work_order_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.update_task(work_order_id, task_id, data)


@router.patch(
    "/{work_order_id}/tasks/{task_id}/status",
    response_model=WorkOrderResponse,
)
async def update_task_status(
    work_order_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskStatusUpdate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.update_task_status(work_order_id, task_id, data)


@router.delete(
    "/{work_order_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    work_order_id: uuid.UUID,
    task_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.delete_task(work_order_id, task_id)


# ── Task Materials ────────────────────────────────────────────────────────────

@router.post(
    "/{work_order_id}/materials",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_material(
    work_order_id: uuid.UUID,
    data: TaskMaterialCreate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.add_material(work_order_id, data)


@router.delete(
    "/{work_order_id}/tasks/{task_id}/materials/{material_id}",
    response_model=TaskResponse,
)
async def remove_material(
    work_order_id: uuid.UUID,
    task_id: uuid.UUID,
    material_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.remove_material(work_order_id, task_id, material_id)


@router.post(
    "/{work_order_id}/tasks/{task_id}/materials/{material_id}/consume",
    response_model=TaskResponse,
)
async def consume_material(
    work_order_id: uuid.UUID,
    task_id: uuid.UUID,
    material_id: uuid.UUID,
    data: TaskMaterialConsume,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.consume_material(work_order_id, task_id, material_id, data)


# ── Purchase Orders ───────────────────────────────────────────────────────────

@router.post(
    "/{work_order_id}/purchase-orders",
    response_model=WorkOrderResponse,
)
async def link_purchase_order(
    work_order_id: uuid.UUID,
    data: WorkOrderPurchaseOrderLink,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.link_purchase_order(work_order_id, data)


@router.delete(
    "/{work_order_id}/purchase-orders/{purchase_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_purchase_order(
    work_order_id: uuid.UUID,
    purchase_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.unlink_purchase_order(work_order_id, purchase_order_id)


@router.post(
    "/{work_order_id}/purchase-orders/new",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_and_link_purchase_order(
    work_order_id: uuid.UUID,
    data: NewPurchaseOrderForWorkOrder,
    db: DbSession,
    _: CurrentUser,
):
    """Creates a new PurchaseOrder and links it to the work order."""
    from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderLineCreate
    from app.services.purchase_order import PurchaseOrderService

    po_svc = PurchaseOrderService(db)
    po_lines = [PurchaseOrderLineCreate(**line) for line in data.lines]
    po = await po_svc.create_order(
        PurchaseOrderCreate(
            supplier_id=data.supplier_id,
            order_date=data.order_date,
            expected_date=data.expected_date,
            notes=data.notes,
            lines=po_lines,
        )
    )
    svc = WorkOrderService(db)
    return await svc.link_purchase_order(
        work_order_id,
        WorkOrderPurchaseOrderLink(purchase_order_id=po.id),
    )


@router.post(
    "/{work_order_id}/purchase-orders/{purchase_order_id}/receive",
    response_model=WorkOrderResponse,
)
async def receive_purchase_order(
    work_order_id: uuid.UUID,
    purchase_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    """Marks a linked PO as received and syncs its lines into the work order's task materials."""
    svc = WorkOrderService(db)
    return await svc.receive_purchase_order_from_work_order(work_order_id, purchase_order_id)


# ── Certifications ────────────────────────────────────────────────────────────

@router.get(
    "/{work_order_id}/certifiable-tasks",
    response_model=list[TaskResponse],
)
async def get_certifiable_tasks(
    work_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.get_certifiable_tasks(work_order_id)


@router.post(
    "/{work_order_id}/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_certification(
    work_order_id: uuid.UUID,
    data: CertificationCreate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.create_certification(work_order_id, data)


@router.post(
    "/{work_order_id}/certifications/{cert_id}/issue",
    response_model=CertificationResponse,
)
async def issue_certification(
    work_order_id: uuid.UUID,
    cert_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.issue_certification(work_order_id, cert_id)


@router.delete(
    "/{work_order_id}/certifications/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certification(
    work_order_id: uuid.UUID,
    cert_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.delete_certification(work_order_id, cert_id)


# ── Delivery Notes ────────────────────────────────────────────────────────────

@router.get(
    "/{work_order_id}/delivery-notes",
    response_model=list[DeliveryNoteResponse],
)
async def list_delivery_notes(
    work_order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.list_delivery_notes(work_order_id)


@router.post(
    "/{work_order_id}/delivery-notes",
    response_model=DeliveryNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_delivery_note(
    work_order_id: uuid.UUID,
    data: DeliveryNoteCreate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.create_delivery_note(work_order_id, data)


@router.get(
    "/{work_order_id}/delivery-notes/{delivery_note_id}",
    response_model=DeliveryNoteResponse,
)
async def get_delivery_note(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.get_delivery_note(work_order_id, delivery_note_id)


@router.patch(
    "/{work_order_id}/delivery-notes/{delivery_note_id}",
    response_model=DeliveryNoteResponse,
)
async def update_delivery_note(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    data: DeliveryNoteUpdate,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.update_delivery_note(work_order_id, delivery_note_id, data)


@router.post(
    "/{work_order_id}/delivery-notes/{delivery_note_id}/issue",
    response_model=DeliveryNoteResponse,
)
async def issue_delivery_note(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    return await svc.issue_delivery_note(work_order_id, delivery_note_id)


@router.delete(
    "/{work_order_id}/delivery-notes/{delivery_note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_delivery_note(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.delete_delivery_note(work_order_id, delivery_note_id)


@router.get("/{work_order_id}/delivery-notes/{delivery_note_id}/pdf")
async def download_delivery_note_pdf(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    pdf_bytes = await svc.generate_delivery_note_pdf(work_order_id, delivery_note_id)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=albaran_{delivery_note_id}.pdf"
        },
    )


@router.post(
    "/{work_order_id}/delivery-notes/{delivery_note_id}/send-email",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def send_delivery_note_email(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    data: SendDocumentEmail,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.send_delivery_note_email(work_order_id, delivery_note_id, data)


@router.get(
    "/{work_order_id}/delivery-notes/{delivery_note_id}/whatsapp-link",
    response_model=WhatsAppLinkResponse,
)
async def get_delivery_note_whatsapp_link(
    work_order_id: uuid.UUID,
    delivery_note_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    phone: str | None = Query(default=None),
):
    svc = WorkOrderService(db)
    return await svc.get_delivery_note_whatsapp_link(
        work_order_id, delivery_note_id, phone
    )


# ── Certification PDF / Email / WhatsApp ──────────────────────────────────────

@router.get("/{work_order_id}/certifications/{cert_id}/pdf")
async def download_certification_pdf(
    work_order_id: uuid.UUID,
    cert_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    pdf_bytes = await svc.generate_certification_pdf(work_order_id, cert_id)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificacion_{cert_id}.pdf"
        },
    )


@router.post(
    "/{work_order_id}/certifications/{cert_id}/send-email",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def send_certification_email(
    work_order_id: uuid.UUID,
    cert_id: uuid.UUID,
    data: SendDocumentEmail,
    db: DbSession,
    _: CurrentUser,
):
    svc = WorkOrderService(db)
    await svc.send_certification_email(work_order_id, cert_id, data)


@router.get(
    "/{work_order_id}/certifications/{cert_id}/whatsapp-link",
    response_model=WhatsAppLinkResponse,
)
async def get_certification_whatsapp_link(
    work_order_id: uuid.UUID,
    cert_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    phone: str | None = Query(default=None),
):
    svc = WorkOrderService(db)
    return await svc.get_certification_whatsapp_link(work_order_id, cert_id, phone)
