import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.resource("inventory://alerts")
    async def inventory_alerts() -> str:
        """Inventory items whose current stock is below the minimum threshold."""
        try:
            data = await client.get("/api/v1/inventory/alerts")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return json.dumps({"error": e.detail, "status_code": e.status_code})
