"""Service layer for the Invoicing module."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus, Payment
from app.models.work_order import Certification, CertificationItem
from app.repositories.budget import BudgetLineRepository
from app.repositories.company_settings import CompanySettingsRepository
from app.repositories.customer import CustomerRepository
from app.repositories.invoice import (
    InvoiceLineRepository,
    InvoiceRepository,
    PaymentRepository,
)
from app.repositories.work_order import (
    CertificationRepository,
    TaskRepository,
    WorkOrderRepository,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceFilters,
    InvoiceFromWorkOrderRequest,
    InvoiceLineCreate,
    InvoiceLineResponse,
    InvoiceLineUpdate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceSummary,
    InvoiceTotals,
    InvoiceUpdate,
    PaymentCreate,
    PaymentReminderResponse,
    PaymentResponse,
    RectificationRequest,
    ReorderLinesRequest,
)
from app.utils.pdf_renderer import render_invoice_pdf_html

logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id
        self._repo = InvoiceRepository(session, tenant_id)
        self._line_repo = InvoiceLineRepository(session, tenant_id)
        self._payment_repo = PaymentRepository(session, tenant_id)
        self._company_repo = CompanySettingsRepository(session, tenant_id)
        self._customer_repo = CustomerRepository(session, tenant_id)
        self._work_order_repo = WorkOrderRepository(session, tenant_id)
        self._cert_repo = CertificationRepository(session, tenant_id)
        self._task_repo = TaskRepository(session, tenant_id)
        self._budget_line_repo = BudgetLineRepository(session, tenant_id)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_invoice(self, data: InvoiceCreate) -> InvoiceResponse:
        """Create a standalone invoice not linked to any work order."""
        company = await self._company_repo.get()
        today = date.today()

        customer = await self._customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        invoice_number = await self._repo.get_next_invoice_number()
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=data.customer_id,
            work_order_id=data.work_order_id,
            status=InvoiceStatus.DRAFT,
            issue_date=data.issue_date or today,
            due_date=data.due_date or (
                today + timedelta(days=company.default_payment_days)
            ),
            tax_rate=data.tax_rate or company.default_tax_rate,
            discount_pct=data.discount_pct,
            notes=data.notes,
            client_notes=data.client_notes,
            tenant_id=self._tenant_id,
        )
        invoice = await self._repo.create(invoice)

        for i, line_data in enumerate(data.lines):
            await self._create_line(invoice.id, line_data, sort_order=i)

        await self._session.commit()
        return await self.get_invoice(invoice.id)

    async def create_from_work_order(
        self, data: InvoiceFromWorkOrderRequest
    ) -> InvoiceResponse:
        """
        Create an invoice from a work order, mixing certifications,
        tasks and manual lines.
        """
        work_order = await self._work_order_repo.get_with_full_detail(
            data.work_order_id
        )
        if not work_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )

        company = await self._company_repo.get()
        today = date.today()
        invoice_number = await self._repo.get_next_invoice_number()

        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=work_order.customer_id,
            work_order_id=data.work_order_id,
            status=InvoiceStatus.DRAFT,
            issue_date=data.issue_date or today,
            due_date=data.due_date or (
                today + timedelta(days=company.default_payment_days)
            ),
            tax_rate=data.tax_rate or company.default_tax_rate,
            discount_pct=data.discount_pct,
            notes=data.notes,
            client_notes=data.client_notes,
            tenant_id=self._tenant_id,
        )
        invoice = await self._repo.create(invoice)
        sort_order = 0

        # Lines from certifications
        for cert_id in data.certification_ids:
            cert = await self._cert_repo.get_by_id(cert_id)
            if not cert or cert.work_order_id != data.work_order_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Certificación {cert_id} no encontrada en esta obra",
                )
            if cert.status.value != "issued":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"La certificación {cert.certification_number} "
                        "debe estar emitida para incluirla en una factura"
                    ),
                )

            for item in (cert.items or []):
                task_name = item.task.name if item.task else f"Tarea {item.task_id}"
                line_data = InvoiceLineCreate(
                    origin_type="certification",
                    origin_id=cert.id,
                    description=task_name,
                    quantity=Decimal("1"),
                    unit_price=item.amount,
                    sort_order=sort_order,
                )
                await self._create_line(invoice.id, line_data, sort_order)
                sort_order += 1

            await self._cert_repo.update(cert, {
                "status": "invoiced",
                "invoice_id": invoice.id,
            })

        # Lines from tasks (direct, no certification)
        already_invoiced_task_ids = await self._get_invoiced_task_ids(
            data.work_order_id
        )
        for task_id in data.task_ids:
            if task_id in already_invoiced_task_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Una o más tareas ya están incluidas en una certificación "
                        "facturada. No se puede facturar dos veces."
                    ),
                )
            task = await self._task_repo.get_by_id(task_id)
            if not task or task.work_order_id != data.work_order_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tarea {task_id} no encontrada en esta obra",
                )
            if task.status.value != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La tarea '{task.name}' debe estar completada",
                )

            amount = await self._calculate_task_amount_for_invoice(task)
            line_data = InvoiceLineCreate(
                origin_type="task",
                origin_id=task.id,
                description=task.name,
                quantity=Decimal("1"),
                unit_price=amount,
                sort_order=sort_order,
            )
            await self._create_line(invoice.id, line_data, sort_order)
            sort_order += 1

        # Manual extra lines
        for extra in data.extra_lines:
            await self._create_line(invoice.id, extra, sort_order)
            sort_order += 1

        await self._session.commit()
        return await self.get_invoice(invoice.id)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list_invoices(
        self, filters: InvoiceFilters
    ) -> InvoiceListResponse:
        invoices, total = await self._repo.search(
            filters.q,
            filters.customer_id,
            filters.work_order_id,
            filters.status,
            filters.overdue_only,
            filters.date_from,
            filters.date_to,
            filters.skip,
            filters.limit,
        )
        return InvoiceListResponse(
            items=[self._build_summary(inv) for inv in invoices],
            total=total,
        )

    async def get_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        return self._build_response(invoice)

    async def update_invoice(
        self, invoice_id: uuid.UUID, data: InvoiceUpdate
    ) -> InvoiceResponse:
        invoice = await self._repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Solo se pueden editar facturas en estado borrador. "
                    "Para modificar una factura enviada, genera una rectificativa."
                ),
            )
        await self._repo.update(invoice, data.model_dump(exclude_none=True))
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def send_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden enviar facturas en estado borrador",
            )
        if not invoice.lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede enviar una factura sin líneas",
            )
        await self._repo.update(invoice, {"status": InvoiceStatus.SENT})
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def cancel_invoice(
        self, invoice_id: uuid.UUID, reason: str
    ) -> InvoiceResponse:
        """
        Cancel a draft invoice. If sent or paid, error 400 — use rectification.
        Reverts any linked certifications back to issued status.
        """
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status in (InvoiceStatus.SENT, InvoiceStatus.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No se puede cancelar una factura enviada o pagada. "
                    "Genera una factura rectificativa."
                ),
            )

        # Revert certifications linked to this invoice back to issued
        await self._session.execute(
            update(Certification)
            .where(Certification.invoice_id == invoice_id)
            .values(status="issued", invoice_id=None)
        )

        notes_update = (invoice.notes or "") + f"\n[Cancelada] {reason}"
        await self._repo.update(invoice, {
            "status": InvoiceStatus.CANCELLED,
            "notes": notes_update,
        })
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def create_rectification(
        self, invoice_id: uuid.UUID, data: RectificationRequest
    ) -> InvoiceResponse:
        """
        Create a rectification invoice that cancels the original.
        Copies all lines with negative unit_price. Original becomes cancelled.
        """
        original = await self._repo.get_with_full_detail(invoice_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if original.status not in (InvoiceStatus.SENT, InvoiceStatus.PAID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden rectificar facturas enviadas o pagadas",
            )
        if original.is_rectification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede rectificar una factura rectificativa",
            )

        invoice_number = await self._repo.get_next_invoice_number(
            is_rectification=True
        )
        today = date.today()
        company = await self._company_repo.get()

        rect = Invoice(
            invoice_number=invoice_number,
            is_rectification=True,
            rectifies_invoice_id=invoice_id,
            customer_id=original.customer_id,
            work_order_id=original.work_order_id,
            status=InvoiceStatus.DRAFT,
            issue_date=today,
            due_date=today + timedelta(days=company.default_payment_days),
            tax_rate=original.tax_rate,
            discount_pct=original.discount_pct,
            notes=(
                f"Rectificativa de {original.invoice_number}. "
                f"Motivo: {data.reason}"
            ),
            client_notes=data.notes,
            tenant_id=self._tenant_id,
        )
        rect = await self._repo.create(rect)

        for i, line in enumerate(original.lines):
            rect_line = InvoiceLine(
                invoice_id=rect.id,
                origin_type=line.origin_type,
                origin_id=line.origin_id,
                sort_order=i,
                description=f"[RECTIFICACIÓN] {line.description}",
                quantity=line.quantity,
                unit=line.unit,
                unit_price=-line.unit_price,
                line_discount_pct=line.line_discount_pct,
            )
            self._session.add(rect_line)

        # Mark original as cancelled
        await self._repo.update(original, {"status": InvoiceStatus.CANCELLED})

        # Revert certifications linked to the original invoice
        await self._session.execute(
            update(Certification)
            .where(Certification.invoice_id == invoice_id)
            .values(status="issued", invoice_id=None)
        )

        await self._session.commit()
        return await self.get_invoice(rect.id)

    async def delete_invoice(self, invoice_id: uuid.UUID) -> None:
        """
        Delete an invoice regardless of status.
        - Reverts linked certifications back to issued (invoice_id=NULL).
        - Nullifies rectifies_invoice_id in any invoice that rectifies this one.
        - Removes the PDF file from disk.
        """
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )

        await self._session.execute(
            update(Certification)
            .where(Certification.invoice_id == invoice_id)
            .values(status="issued", invoice_id=None)
        )
        await self._session.execute(
            update(Invoice)
            .where(Invoice.rectifies_invoice_id == invoice_id)
            .values(rectifies_invoice_id=None)
        )

        if invoice.pdf_path:
            pdf_file = Path(invoice.pdf_path)
            if pdf_file.exists():
                pdf_file.unlink()

        await self._repo.delete(invoice)
        await self._session.commit()
        logger.info(
            "invoice.deleted id=%s number=%s",
            invoice_id,
            invoice.invoice_number,
        )

    # ── Payments ──────────────────────────────────────────────────────────────

    async def register_payment(
        self, invoice_id: uuid.UUID, data: PaymentCreate
    ) -> InvoiceResponse:
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status != InvoiceStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden registrar cobros en facturas enviadas",
            )

        totals = self._calculate_totals(invoice)
        if data.amount > totals.pending_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El importe ({data.amount}€) supera el pendiente "
                    f"de cobro ({totals.pending_amount}€)"
                ),
            )

        payment = Payment(
            invoice_id=invoice_id,
            amount=data.amount,
            payment_date=data.payment_date,
            method=data.method,
            reference=data.reference,
            notes=data.notes,
        )
        self._session.add(payment)

        new_total_paid = totals.total_paid + data.amount
        if new_total_paid >= totals.total:
            await self._repo.update(invoice, {"status": InvoiceStatus.PAID})

        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def delete_payment(
        self, invoice_id: uuid.UUID, payment_id: uuid.UUID
    ) -> InvoiceResponse:
        payment = await self._payment_repo.get_by_id(payment_id)
        if not payment or payment.invoice_id != invoice_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pago no encontrado",
            )

        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )

        if invoice.status == InvoiceStatus.PAID:
            await self._repo.update(invoice, {"status": InvoiceStatus.SENT})

        await self._payment_repo.delete(payment)
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    # ── Lines (manual editing) ─────────────────────────────────────────────────

    async def add_line(
        self, invoice_id: uuid.UUID, data: InvoiceLineCreate
    ) -> InvoiceResponse:
        invoice = await self._repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden añadir líneas a facturas en borrador",
            )
        await self._create_line(invoice_id, data, data.sort_order)
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def update_line(
        self,
        invoice_id: uuid.UUID,
        line_id: uuid.UUID,
        data: InvoiceLineUpdate,
    ) -> InvoiceResponse:
        line = await self._line_repo.get_by_id(line_id)
        if not line or line.invoice_id != invoice_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Línea no encontrada",
            )
        invoice = await self._repo.get_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden editar líneas de facturas en borrador",
            )
        await self._line_repo.update(line, data.model_dump(exclude_none=True))
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def delete_line(
        self, invoice_id: uuid.UUID, line_id: uuid.UUID
    ) -> InvoiceResponse:
        line = await self._line_repo.get_by_id(line_id)
        if not line or line.invoice_id != invoice_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Línea no encontrada",
            )
        invoice = await self._repo.get_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar líneas de facturas en borrador",
            )
        await self._line_repo.delete(line)
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    async def reorder_lines(
        self, invoice_id: uuid.UUID, data: ReorderLinesRequest
    ) -> InvoiceResponse:
        invoice = await self._repo.get_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada o no editable",
            )
        for i, line_id in enumerate(data.line_ids):
            await self._session.execute(
                update(InvoiceLine)
                .where(InvoiceLine.id == line_id)
                .where(InvoiceLine.invoice_id == invoice_id)
                .values(sort_order=i)
            )
        await self._session.commit()
        return await self.get_invoice(invoice_id)

    # ── PDF ───────────────────────────────────────────────────────────────────

    async def generate_pdf(self, invoice_id: uuid.UUID) -> bytes:
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )

        company = await self._company_repo.get()
        totals = self._calculate_totals(invoice)

        html_content = render_invoice_pdf_html(invoice, company, totals)

        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()

        upload_dir = Path(settings.UPLOAD_DIR) / "invoices" / str(invoice_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = upload_dir / f"factura_{invoice.invoice_number}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        await self._repo.update(invoice, {"pdf_path": str(pdf_path)})
        await self._session.commit()
        return pdf_bytes

    # ── Reminder ──────────────────────────────────────────────────────────────

    async def get_payment_reminder(
        self, invoice_id: uuid.UUID
    ) -> PaymentReminderResponse:
        invoice = await self._repo.get_with_full_detail(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if invoice.status != InvoiceStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Solo se pueden generar recordatorios de facturas enviadas"
                ),
            )

        company = await self._company_repo.get()
        totals = self._calculate_totals(invoice)
        days_overdue = (date.today() - invoice.due_date).days

        overdue_text = (
            f"Esta factura venció hace {days_overdue} días."
            if days_overdue > 0
            else (
                f"Esta factura vence el "
                f"{invoice.due_date.strftime('%d/%m/%Y')}."
            )
        )

        text = (
            f"Estimado/a {invoice.customer.name},\n\n"
            "Le recordamos que tiene pendiente de pago la siguiente factura:\n\n"
            f"  Nº Factura: {invoice.invoice_number}\n"
            f"  Fecha:      {invoice.issue_date.strftime('%d/%m/%Y')}\n"
            f"  Importe:    {totals.pending_amount:.2f} €\n"
            f"  {overdue_text}\n\n"
            "Datos para el pago:\n"
            f"  IBAN: {company.bank_account or '(configurar en ajustes)'}\n"
            f"  Beneficiario: {company.company_name}\n"
            f"  Concepto: {invoice.invoice_number}\n\n"
            "Si ya ha realizado el pago, ignore este mensaje.\n"
            "Ante cualquier duda, no dude en contactarnos.\n\n"
            "Un saludo,\n"
            f"{company.company_name}\n"
            f"{company.phone or ''}\n"
            f"{company.email or ''}"
        )

        return PaymentReminderResponse(
            invoice_number=invoice.invoice_number,
            customer_name=invoice.customer.name,
            pending_amount=float(totals.pending_amount),
            days_overdue=max(0, days_overdue),
            reminder_text=text,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _calculate_totals(self, invoice: Invoice) -> InvoiceTotals:
        subtotal = sum(
            (
                line.quantity * line.unit_price
                * (1 - line.line_discount_pct / 100)
                for line in (invoice.lines or [])
            ),
            Decimal("0"),
        )
        discount_amount = subtotal * (invoice.discount_pct / 100)
        taxable_base = subtotal - discount_amount
        tax_amount = taxable_base * (invoice.tax_rate / 100)
        total = taxable_base + tax_amount

        total_paid = sum(
            (p.amount for p in (invoice.payments or [])), Decimal("0")
        )
        pending = total - total_paid

        return InvoiceTotals(
            subtotal_before_discount=subtotal.quantize(Decimal("0.01")),
            discount_amount=discount_amount.quantize(Decimal("0.01")),
            taxable_base=taxable_base.quantize(Decimal("0.01")),
            tax_amount=tax_amount.quantize(Decimal("0.01")),
            total=total.quantize(Decimal("0.01")),
            total_paid=total_paid.quantize(Decimal("0.01")),
            pending_amount=max(Decimal("0"), pending).quantize(
                Decimal("0.01")
            ),
            is_fully_paid=total_paid >= total,
        )

    def _get_effective_status(self, invoice: Invoice) -> str:
        totals = self._calculate_totals(invoice)
        if invoice.status == InvoiceStatus.SENT:
            if totals.total_paid > 0:
                return "partially_paid"
            if invoice.due_date < date.today():
                return "overdue"
        return invoice.status.value

    def _get_days_overdue(self, invoice: Invoice) -> int:
        if (
            invoice.status == InvoiceStatus.SENT
            and invoice.due_date < date.today()
        ):
            return (date.today() - invoice.due_date).days
        return 0

    async def _create_line(
        self,
        invoice_id: uuid.UUID,
        data: InvoiceLineCreate,
        sort_order: int,
    ) -> InvoiceLine:
        line = InvoiceLine(
            invoice_id=invoice_id,
            origin_type=data.origin_type,
            origin_id=data.origin_id,
            description=data.description,
            quantity=data.quantity,
            unit=data.unit,
            unit_price=data.unit_price,
            line_discount_pct=data.line_discount_pct,
            sort_order=sort_order,
        )
        self._session.add(line)
        await self._session.flush()
        return line

    async def _calculate_task_amount_for_invoice(
        self, task
    ) -> Decimal:
        if not task.origin_budget_line_id:
            return task.unit_price or Decimal("0.0")
        line = await self._budget_line_repo.get_by_id(
            task.origin_budget_line_id
        )
        if not line:
            return task.unit_price or Decimal("0.0")
        subtotal = line.quantity * line.unit_price
        if line.line_discount_pct > 0:
            subtotal *= 1 - line.line_discount_pct / 100
        return subtotal.quantize(Decimal("0.01"))

    async def _get_invoiced_task_ids(
        self, work_order_id: uuid.UUID
    ) -> set[uuid.UUID]:
        from sqlalchemy import select

        result = await self._session.execute(
            select(CertificationItem.task_id)
            .join(Certification)
            .where(Certification.work_order_id == work_order_id)
            .where(Certification.status == "invoiced")
        )
        return {row[0] for row in result.all()}

    def _build_summary(self, invoice: Invoice) -> InvoiceSummary:
        totals = self._calculate_totals(invoice)
        return InvoiceSummary(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            is_rectification=invoice.is_rectification,
            rectifies_invoice_id=invoice.rectifies_invoice_id,
            customer_id=invoice.customer_id,
            customer_name=(
                invoice.customer.name if invoice.customer else ""
            ),
            work_order_id=invoice.work_order_id,
            work_order_number=(
                invoice.work_order.work_order_number
                if invoice.work_order
                else None
            ),
            status=invoice.status.value,
            effective_status=self._get_effective_status(invoice),
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            total=totals.total,
            total_paid=totals.total_paid,
            pending_amount=totals.pending_amount,
            days_overdue=self._get_days_overdue(invoice),
            has_pdf=invoice.pdf_path is not None,
            created_at=invoice.created_at,
        )

    def _build_response(self, invoice: Invoice) -> InvoiceResponse:
        totals = self._calculate_totals(invoice)
        summary = self._build_summary(invoice)
        lines = [
            InvoiceLineResponse(
                id=line.id,
                invoice_id=line.invoice_id,
                origin_type=line.origin_type.value,
                origin_id=line.origin_id,
                sort_order=line.sort_order,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                line_discount_pct=line.line_discount_pct,
                subtotal=(
                    line.quantity * line.unit_price
                    * (1 - line.line_discount_pct / 100)
                ).quantize(Decimal("0.01")),
            )
            for line in (invoice.lines or [])
        ]
        return InvoiceResponse(
            **summary.model_dump(),
            discount_pct=invoice.discount_pct,
            tax_rate=invoice.tax_rate,
            notes=invoice.notes,
            client_notes=invoice.client_notes,
            lines=lines,
            payments=[
                PaymentResponse.model_validate(p)
                for p in (invoice.payments or [])
            ],
            totals=totals,
            updated_at=invoice.updated_at,
        )
