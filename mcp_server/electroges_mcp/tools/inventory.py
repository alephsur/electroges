import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def list_inventory(
        query: str | None = None,
        active_only: bool = True,
        limit: int = 30,
    ) -> str:
        """List inventory items with optional text search.

        Args:
            query: Search term to filter by name, SKU or description.
            active_only: If True, returns only active items. Default: True.
            limit: Maximum number of results.
        """
        try:
            params: dict = {"limit": limit, "skip": 0, "active_only": active_only}
            if query:
                params["search"] = query
            data = await client.get("/api/v1/inventory", params=params)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al listar inventario: {e.detail}"

    @mcp.tool()
    async def get_inventory_alerts() -> str:
        """Get all inventory items whose stock is at or below the minimum threshold.

        Returns items ordered by criticality (most below minimum first).
        Use this to identify what needs to be reordered before starting new work orders.
        """
        try:
            data = await client.get("/api/v1/inventory/alerts")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener alertas de inventario: {e.detail}"

    @mcp.tool()
    async def get_inventory_item(item_id: str) -> str:
        """Get full details of an inventory item including stock movements history
        and supplier pricing.
        """
        try:
            item = await client.get(f"/api/v1/inventory/{item_id}")
            movements = await client.get(
                f"/api/v1/inventory/{item_id}/movements",
                params={"limit": 20},
            )
            return json.dumps(
                {"item": item, "recent_movements": movements},
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except ApiError as e:
            return f"Error al obtener artículo {item_id}: {e.detail}"
