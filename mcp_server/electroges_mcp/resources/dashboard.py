import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.resource("dashboard://summary")
    async def dashboard_summary() -> str:
        """Business KPIs: active work orders, monthly billing, pending collections, low stock."""
        try:
            data = await client.get("/api/v1/dashboard/summary")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return json.dumps({"error": e.detail, "status_code": e.status_code})
