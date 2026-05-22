from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.prompt()
    def analyze_customer(customer_id: str) -> str:
        """Full commercial analysis of a customer: history, open work, pending debt."""
        return f"""Realiza un análisis completo del cliente con ID {customer_id} en ElectroGes.

Sigue estos pasos en orden:

1. **Ficha del cliente** — usa `get_customer` con customer_id="{customer_id}"
2. **Historial de actividad** — usa `get_customer_timeline` con customer_id="{customer_id}"
3. **Presupuestos** — usa `list_budgets` con customer_id="{customer_id}" (sin filtro de status para ver todos)
4. **Obras** — usa `list_work_orders` con customer_id="{customer_id}" (sin filtro de status)
5. **Facturas** — usa `list_invoices` con customer_id="{customer_id}" (sin filtro de status)

Con toda esa información, elabora un informe que incluya:

### Resumen ejecutivo
- Estado actual de la relación comercial
- Valor total facturado históricamente

### Situación actual
- Obras en curso: nombre, estado, fecha de inicio
- Presupuestos pendientes de respuesta del cliente
- Deuda pendiente: facturas enviadas o vencidas sin cobrar (monto total)

### Alertas
- Facturas vencidas (status='overdue')
- Presupuestos que van a expirar próximamente
- Obras en estado 'pending_closure' que podrían facturarse ya

### Oportunidades comerciales
- Patrones detectados (obras recurrentes, materiales habituales)
- Sugerencias de seguimiento o upsell basadas en el historial
"""

    @mcp.prompt()
    def suggest_budget_from_visit(
        visit_id: str,
        project_type: str | None = None,
    ) -> str:
        """Generate budget line suggestions from a site visit's technical notes."""
        type_context = f" de tipo '{project_type}'" if project_type else ""
        return f"""Analiza la visita técnica con ID {visit_id} y genera una propuesta de líneas de presupuesto.

Pasos:
1. Obtén los detalles de la visita con `get_site_visit` (visit_id="{visit_id}")
2. Revisa las notas técnicas, alcance del trabajo y materiales estimados
3. Consulta el inventario con `list_inventory` para encontrar materiales disponibles y sus precios

Para un proyecto eléctrico{type_context}, propón líneas del presupuesto con este formato:

| Tipo | Descripción | Cantidad | Precio unitario (PVP) | Coste unitario |
|------|-------------|----------|-----------------------|----------------|
| labor | ... | ... horas | €/hora | €/hora |
| material | ... | ... uds | €/ud | €/ud |

Consideraciones:
- Las líneas de tipo 'labor' usan horas como unidad
- El margen interno (diferencia precio - coste) NO se muestra al cliente
- Incluye una línea de "otros" para gastos de desplazamiento si aplica
- Ajusta el IVA al 21% por defecto (instalaciones eléctricas en España)

Después de proponer las líneas, usa `create_budget` para crear el presupuesto y luego
`add_budget_line` para cada línea aprobada.
"""

    @mcp.prompt()
    def work_order_progress_report(work_order_id: str) -> str:
        """Status and profitability report for an active work order."""
        return f"""Genera un informe de estado y rentabilidad para la obra con ID {work_order_id}.

Pasos:
1. Obtén los datos completos con `get_work_order` (work_order_id="{work_order_id}")
2. Obtén los KPIs con `get_work_order_kpis` (work_order_id="{work_order_id}")

Redacta un informe con las siguientes secciones:

### Estado general
- Estado actual y fecha de inicio
- Progreso global (% de tareas completadas)

### Tareas
- Lista de tareas con su estado (pendiente / en curso / completada)
- Horas estimadas vs horas reales por tarea
- Tareas bloqueadas o con retraso

### Materiales
- Material previsto vs consumido por tarea
- Desviaciones significativas en consumo

### Rentabilidad
- Coste real acumulado vs coste presupuestado
- Margen actual
- Proyección al cierre basada en el avance

### Próximos pasos recomendados
- Si todas las tareas están completas: sugerir cerrar la obra y crear la factura con `create_invoice_from_work_order`
- Si hay desviaciones: señalar las causas y qué acciones tomar
"""

    @mcp.prompt()
    def invoice_collection_strategy(customer_id: str | None = None) -> str:
        """Build a collections action plan for overdue invoices."""
        scope = f"del cliente {customer_id}" if customer_id else "de todos los clientes"
        params_hint = f'customer_id="{customer_id}", status="overdue"' if customer_id else 'status="overdue"'
        return f"""Elabora un plan de acción de cobros para las facturas vencidas {scope}.

Pasos:
1. Obtén las facturas vencidas con `list_invoices` ({params_hint}, limit=50)
2. Para cada cliente con facturas vencidas, usa `get_customer` para obtener sus datos de contacto

Estructura el plan así:

### Resumen de deuda vencida
- Total de facturas vencidas
- Importe total pendiente
- Desglose por antigüedad: < 30 días / 30-60 días / > 60 días

### Lista de acciones prioritarias
Ordena por importe descendente. Para cada factura:
- Cliente: nombre y teléfono/email de contacto
- Factura: número, importe, fecha de vencimiento, días de retraso
- Acción recomendada:
  - < 30 días: recordatorio amistoso por email/teléfono
  - 30-60 días: segundo aviso formal
  - > 60 días: escalar (burofax, gestión de deuda)

### Facturas ya enviadas (status='sent') próximas a vencer
Incluye también las facturas enviadas que vencen en los próximos 7 días para prevención.
"""
