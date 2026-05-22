import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def list_budgets(
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """List budgets with optional filters.

        Args:
            customer_id: Filter by customer UUID.
            status: Filter by status — 'draft', 'sent', 'accepted', 'rejected', 'expired'.
            limit: Maximum number of results.
        """
        try:
            params: dict = {"limit": limit, "skip": 0}
            if customer_id:
                params["customer_id"] = customer_id
            if status:
                params["status"] = status
            data = await client.get("/api/v1/budgets", params=params)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al listar presupuestos: {e.detail}"

    @mcp.tool()
    async def get_budget(budget_id: str) -> str:
        """Get full budget details including all lines, sections, and economic totals.

        Internal margin data is included (unit_cost, margin %) — never expose this
        to the customer.
        """
        try:
            data = await client.get(f"/api/v1/budgets/{budget_id}")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener presupuesto {budget_id}: {e.detail}"

    @mcp.tool()
    async def create_budget(
        customer_id: str,
        title: str,
        valid_until: str,
        site_visit_id: str | None = None,
        tax_rate: float = 21.0,
        discount: float = 0.0,
        notes: str | None = None,
    ) -> str:
        """Create a new budget for a customer.

        Args:
            customer_id: UUID of the customer.
            title: Descriptive title for the budget.
            valid_until: Expiration date in ISO format 'YYYY-MM-DD'.
            site_visit_id: Link to a site visit (recommended when one exists).
            tax_rate: VAT percentage. Default: 21.0.
            discount: Global discount percentage. Default: 0.
            notes: Internal or customer-facing notes.

        After creating the budget, use add_budget_line to add line items.
        Use send_budget once it's ready to notify the customer.
        """
        try:
            payload: dict = {
                "customer_id": customer_id,
                "title": title,
                "valid_until": valid_until,
                "tax_rate": tax_rate,
                "discount": discount,
            }
            if site_visit_id:
                payload["site_visit_id"] = site_visit_id
            if notes:
                payload["notes"] = notes
            data = await client.post("/api/v1/budgets", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al crear presupuesto: {e.detail}"

    @mcp.tool()
    async def add_budget_line(
        budget_id: str,
        line_type: str,
        description: str,
        quantity: float,
        unit_price: float,
        unit_cost: float | None = None,
        material_id: str | None = None,
    ) -> str:
        """Add a line item to a budget.

        Args:
            budget_id: UUID of the budget.
            line_type: Type of line — 'labor', 'material', or 'other'.
            description: Description visible to the customer.
            quantity: Quantity (hours for labor, units for material).
            unit_price: Sale price per unit (shown to customer).
            unit_cost: Internal cost per unit (never shown to customer). Used to
                       calculate margin. Required for accurate profitability tracking.
            material_id: Link to an inventory item UUID (optional, for 'material' lines).
        """
        try:
            payload: dict = {
                "line_type": line_type,
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
            }
            if unit_cost is not None:
                payload["unit_cost"] = unit_cost
            if material_id:
                payload["material_id"] = material_id
            data = await client.post(f"/api/v1/budgets/{budget_id}/lines", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al añadir línea al presupuesto {budget_id}: {e.detail}"

    @mcp.tool()
    async def send_budget(budget_id: str) -> str:
        """Mark a budget as sent to the customer.

        Transitions the budget from 'draft' to 'sent'. The customer can then
        accept or reject it. Use accept_budget or reject_budget next.
        """
        try:
            data = await client.post(f"/api/v1/budgets/{budget_id}/send")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al enviar presupuesto {budget_id}: {e.detail}"

    @mcp.tool()
    async def accept_budget(budget_id: str) -> str:
        """Accept a budget and automatically create a work order from it.

        Transitions the budget to 'accepted' and creates a WorkOrder with tasks
        and materials derived from the budget lines. Returns both the updated
        budget and the new work order.
        """
        try:
            data = await client.post(f"/api/v1/budgets/{budget_id}/accept")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al aceptar presupuesto {budget_id}: {e.detail}"

    @mcp.tool()
    async def reject_budget(budget_id: str, rejection_reason: str | None = None) -> str:
        """Reject a budget. It remains on record but no work order is created.

        Args:
            budget_id: UUID of the budget to reject.
            rejection_reason: Optional reason for rejection (stored internally).
        """
        try:
            payload: dict = {}
            if rejection_reason:
                payload["rejection_reason"] = rejection_reason
            data = await client.post(f"/api/v1/budgets/{budget_id}/reject", data=payload or None)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al rechazar presupuesto {budget_id}: {e.detail}"

    @mcp.tool()
    async def create_new_budget_version(budget_id: str) -> str:
        """Create a new version of an existing budget (for revision requests).

        Increments the version number and creates a draft copy. Useful when
        the customer requests changes to a sent budget.
        """
        try:
            data = await client.post(f"/api/v1/budgets/{budget_id}/new-version")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al crear nueva versión del presupuesto {budget_id}: {e.detail}"
