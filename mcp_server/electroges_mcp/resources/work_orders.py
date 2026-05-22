import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.resource("work-orders://active")
    async def active_work_orders() -> str:
        """All work orders currently in progress (status: draft or in_progress)."""
        try:
            draft = await client.get("/api/v1/work-orders", params={"status": "draft", "limit": 50})
            in_progress = await client.get("/api/v1/work-orders", params={"status": "in_progress", "limit": 50})
            return json.dumps(
                {
                    "draft": draft.get("items", []),
                    "in_progress": in_progress.get("items", []),
                    "total_draft": draft.get("total", 0),
                    "total_in_progress": in_progress.get("total", 0),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except ApiError as e:
            return json.dumps({"error": e.detail, "status_code": e.status_code})

    @mcp.resource("work-order://{work_order_id}/details")
    async def work_order_details(work_order_id: str) -> str:
        """Work order full details including tasks, materials, and KPIs."""
        try:
            wo = await client.get(f"/api/v1/work-orders/{work_order_id}")
            kpis = await client.get(f"/api/v1/work-orders/{work_order_id}/kpis")
            return json.dumps(
                {"work_order": wo, "kpis": kpis},
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except ApiError as e:
            return json.dumps({"error": e.detail, "status_code": e.status_code})
