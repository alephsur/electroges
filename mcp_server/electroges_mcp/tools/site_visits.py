import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def list_site_visits(
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """List site visits with optional filters.

        Args:
            customer_id: Filter by customer UUID.
            status: Filter by status — 'scheduled', 'completed', or 'cancelled'.
            limit: Maximum number of results to return.
        """
        try:
            params: dict = {"limit": limit, "skip": 0}
            if customer_id:
                params["customer_id"] = customer_id
            if status:
                params["status"] = status
            data = await client.get("/api/v1/site-visits", params=params)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al listar visitas técnicas: {e.detail}"

    @mcp.tool()
    async def get_site_visit(visit_id: str) -> str:
        """Get full details of a site visit including materials, photos and documents."""
        try:
            data = await client.get(f"/api/v1/site-visits/{visit_id}")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener visita {visit_id}: {e.detail}"

    @mcp.tool()
    async def create_site_visit(
        customer_id: str,
        address: str,
        visit_date: str,
        description: str | None = None,
        work_scope: str | None = None,
        technical_notes: str | None = None,
        estimated_duration_minutes: int | None = None,
    ) -> str:
        """Schedule a new site visit for a customer.

        Args:
            customer_id: UUID of the customer.
            address: Full address where the visit will take place.
            visit_date: ISO 8601 datetime string, e.g. '2025-06-15T10:00:00'.
            description: Brief description of what the visit is about.
            work_scope: Detailed scope of work to assess.
            technical_notes: Technical observations from the visit.
            estimated_duration_minutes: Expected duration in minutes.

        After completing the visit, use update_site_visit_status to mark it as
        'completed' and then create_budget to generate a budget from it.
        """
        try:
            payload: dict = {
                "customer_id": customer_id,
                "address": address,
                "visit_date": visit_date,
            }
            if description:
                payload["description"] = description
            if work_scope:
                payload["work_scope"] = work_scope
            if technical_notes:
                payload["technical_notes"] = technical_notes
            if estimated_duration_minutes is not None:
                payload["estimated_duration"] = estimated_duration_minutes
            data = await client.post("/api/v1/site-visits", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al crear visita técnica: {e.detail}"

    @mcp.tool()
    async def update_site_visit_status(
        visit_id: str,
        status: str,
        technical_notes: str | None = None,
    ) -> str:
        """Update the status of a site visit.

        Args:
            visit_id: UUID of the site visit.
            status: New status — 'scheduled', 'completed', or 'cancelled'.
            technical_notes: Add or update technical notes (optional).
        """
        try:
            payload: dict = {"status": status}
            if technical_notes is not None:
                payload["technical_notes"] = technical_notes
            data = await client.patch(f"/api/v1/site-visits/{visit_id}/status", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al actualizar estado de visita {visit_id}: {e.detail}"
