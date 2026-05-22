import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.tool()
    async def list_work_orders(
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> str:
        """List work orders with optional filters.

        Args:
            customer_id: Filter by customer UUID.
            status: Filter by status — 'draft', 'in_progress', 'pending_closure', 'closed'.
            limit: Maximum number of results.
        """
        try:
            params: dict = {"limit": limit, "skip": 0}
            if customer_id:
                params["customer_id"] = customer_id
            if status:
                params["status"] = status
            data = await client.get("/api/v1/work-orders", params=params)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al listar obras: {e.detail}"

    @mcp.tool()
    async def get_work_order(work_order_id: str) -> str:
        """Get full work order details: tasks, materials, and progress data."""
        try:
            data = await client.get(f"/api/v1/work-orders/{work_order_id}")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener obra {work_order_id}: {e.detail}"

    @mcp.tool()
    async def get_work_order_kpis(work_order_id: str) -> str:
        """Get profitability and progress KPIs for a work order.

        Returns: total cost, total revenue, margin, hours worked vs estimated,
        material consumption rate, and overall completion percentage.
        """
        try:
            data = await client.get(f"/api/v1/work-orders/{work_order_id}/kpis")
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al obtener KPIs de obra {work_order_id}: {e.detail}"

    @mcp.tool()
    async def update_work_order_status(work_order_id: str, status: str) -> str:
        """Change the status of a work order.

        Args:
            work_order_id: UUID of the work order.
            status: New status — 'draft', 'in_progress', 'pending_closure', or 'closed'.

        Status flow: draft → in_progress → pending_closure (auto when all tasks done) → closed.
        Closing a work order is the prerequisite for generating the final invoice.
        """
        try:
            data = await client.patch(
                f"/api/v1/work-orders/{work_order_id}/status",
                data={"status": status},
            )
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al actualizar estado de obra {work_order_id}: {e.detail}"

    @mcp.tool()
    async def add_task(
        work_order_id: str,
        name: str,
        description: str | None = None,
        estimated_hours: float | None = None,
    ) -> str:
        """Add a task to a work order.

        Args:
            work_order_id: UUID of the work order.
            name: Short name for the task.
            description: Detailed description of the work to be done.
            estimated_hours: Expected hours to complete the task.
        """
        try:
            payload: dict = {"name": name}
            if description:
                payload["description"] = description
            if estimated_hours is not None:
                payload["estimated_hours"] = estimated_hours
            data = await client.post(f"/api/v1/work-orders/{work_order_id}/tasks", data=payload)
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al añadir tarea a obra {work_order_id}: {e.detail}"

    @mcp.tool()
    async def update_task_status(
        work_order_id: str,
        task_id: str,
        status: str,
        actual_hours: float | None = None,
    ) -> str:
        """Update the status (and optionally actual hours) of a task.

        Args:
            work_order_id: UUID of the work order.
            task_id: UUID of the task.
            status: New status — 'pending', 'in_progress', or 'completed'.
            actual_hours: Real hours spent (update when marking as completed).

        When all tasks in a work order reach 'completed', the work order
        automatically transitions to 'pending_closure'.
        """
        try:
            payload: dict = {"status": status}
            if actual_hours is not None:
                payload["actual_hours"] = actual_hours
            data = await client.patch(
                f"/api/v1/work-orders/{work_order_id}/tasks/{task_id}/status",
                data=payload,
            )
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al actualizar estado de tarea {task_id}: {e.detail}"

    @mcp.tool()
    async def consume_material(
        work_order_id: str,
        task_id: str,
        material_id: str,
        quantity: float,
    ) -> str:
        """Record actual material consumption for a task.

        Args:
            work_order_id: UUID of the work order.
            task_id: UUID of the task.
            material_id: UUID of the task material entry (not the inventory item).
            quantity: Actual quantity consumed.

        This updates consumed_quantity on the TaskMaterial and triggers a stock
        movement in the inventory.
        """
        try:
            data = await client.post(
                f"/api/v1/work-orders/{work_order_id}/tasks/{task_id}/materials/{material_id}/consume",
                data={"quantity": quantity},
            )
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except ApiError as e:
            return f"Error al registrar consumo de material {material_id}: {e.detail}"
