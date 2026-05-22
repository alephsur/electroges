import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def search_customers(query: str, limit: int = 20) -> str:
        """Search customers by name, NIF/CIF, email or phone.

        Returns a list of matching customers with their basic data.
        Use get_customer for full details of a specific customer.
        """
        try:
            data = await client.get(
                "/api/v1/customers",
                params={"search": query, "limit": limit, "skip": 0},
            )
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al buscar clientes: {e.detail}"

    @mcp.tool()
    async def get_customer(customer_id: str) -> str:
        """Get full customer profile: contact data, addresses, and documents.

        Use get_customer_timeline to also see the customer's activity history.
        """
        try:
            data = await client.get(f"/api/v1/customers/{customer_id}")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener cliente {customer_id}: {e.detail}"

    @mcp.tool()
    async def get_customer_timeline(customer_id: str, limit: int = 30) -> str:
        """Get the unified activity timeline for a customer.

        Shows all events: site visits, budgets, work orders, invoices — ordered
        chronologically. Useful to understand the full commercial history.
        """
        try:
            data = await client.get(
                f"/api/v1/customers/{customer_id}/timeline",
                params={"limit": limit},
            )
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener timeline del cliente {customer_id}: {e.detail}"

    @mcp.tool()
    async def create_customer(
        name: str,
        tax_id: str,
        customer_type: str = "individual",
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Create a new customer in ElectroGes.

        Args:
            name: Full name or company name.
            tax_id: NIF (individuals) or CIF (companies).
            customer_type: 'individual' or 'company'. Default: 'individual'.
            email: Contact email address.
            phone: Contact phone number.
            notes: Internal notes about the customer.

        Returns the created customer with its assigned ID.
        """
        try:
            payload = {
                "name": name,
                "tax_id": tax_id,
                "customer_type": customer_type,
            }
            if email:
                payload["email"] = email
            if phone:
                payload["phone"] = phone
            if notes:
                payload["notes"] = notes
            data = await client.post("/api/v1/customers", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al crear cliente: {e.detail}"
