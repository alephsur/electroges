import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def list_invoices(
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """List invoices with optional filters.

        Args:
            customer_id: Filter by customer UUID.
            status: Filter by status — 'draft', 'sent', 'paid', 'overdue'.
            limit: Maximum number of results.
        """
        try:
            params: dict = {"limit": limit, "skip": 0}
            if customer_id:
                params["customer_id"] = customer_id
            if status:
                params["status"] = status
            data = await client.get("/api/v1/invoices", params=params)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al listar facturas: {e.detail}"

    @mcp.tool()
    async def get_invoice(invoice_id: str) -> str:
        """Get full invoice details including lines, payments, and totals."""
        try:
            data = await client.get(f"/api/v1/invoices/{invoice_id}")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener factura {invoice_id}: {e.detail}"

    @mcp.tool()
    async def create_invoice_from_work_order(
        work_order_id: str,
        issue_date: str | None = None,
        due_date: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Create an invoice from a completed work order.

        Args:
            work_order_id: UUID of the work order (should be in 'pending_closure' or 'closed').
            issue_date: Invoice date in 'YYYY-MM-DD' format. Defaults to today.
            due_date: Payment due date in 'YYYY-MM-DD' format.
            notes: Additional notes for the invoice.

        Lines are derived from the work order's budget. After creating the invoice,
        use send_invoice to notify the customer and register_payment when paid.
        """
        try:
            payload: dict = {"work_order_id": work_order_id}
            if issue_date:
                payload["issue_date"] = issue_date
            if due_date:
                payload["due_date"] = due_date
            if notes:
                payload["notes"] = notes
            data = await client.post("/api/v1/invoices/from-work-order", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al crear factura desde obra {work_order_id}: {e.detail}"

    @mcp.tool()
    async def send_invoice(invoice_id: str) -> str:
        """Mark an invoice as sent to the customer.

        Transitions the invoice from 'draft' to 'sent'. If SMTP is configured,
        sends an email with the PDF attached.
        """
        try:
            data = await client.post(f"/api/v1/invoices/{invoice_id}/send")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al enviar factura {invoice_id}: {e.detail}"

    @mcp.tool()
    async def register_payment(
        invoice_id: str,
        amount: float,
        payment_date: str,
        method: str = "transfer",
        reference: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Register a payment (full or partial) for an invoice.

        Args:
            invoice_id: UUID of the invoice.
            amount: Amount paid (can be less than total for partial payment).
            payment_date: Date of the payment in 'YYYY-MM-DD' format.
            method: Payment method — 'cash', 'transfer', 'card', or 'check'.
            reference: Bank reference number or cheque number (optional).
            notes: Additional notes about this payment.

        When the sum of payments equals the invoice total, the invoice
        automatically transitions to 'paid'.
        """
        try:
            payload: dict = {
                "amount": amount,
                "payment_date": payment_date,
                "method": method,
            }
            if reference:
                payload["reference"] = reference
            if notes:
                payload["notes"] = notes
            data = await client.post(f"/api/v1/invoices/{invoice_id}/payments", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al registrar pago en factura {invoice_id}: {e.detail}"

    @mcp.tool()
    async def get_overdue_invoices(limit: int = 50) -> str:
        """Get all overdue invoices sorted by days overdue.

        Useful for collections follow-up. Returns customer name, invoice number,
        total amount, due date, and days overdue for each invoice.
        """
        try:
            data = await client.get("/api/v1/invoices", params={"status": "overdue", "limit": limit})
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener facturas vencidas: {e.detail}"
