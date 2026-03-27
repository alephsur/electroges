# CLAUDE.md — ElectroGes

## Descripción del proyecto

**ElectroGes** es un sistema de gestión integral para una empresa pequeña de instalaciones eléctricas. El objetivo es digitalizar y centralizar las operaciones del negocio en una única plataforma web, cubriendo la gestión de clientes, visitas técnicas, presupuestos, obras, facturación, inventario y proveedores.

Actualmente la empresa es un autónomo, pero el sistema debe estar diseñado para escalar a un equipo de 2–10 personas sin cambios destructivos en el modelo de datos.

---

## Stack tecnológico obligatorio

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy async 2.0, Alembic, uv (gestor de dependencias), ruff (linter/formatter) |
| Frontend | React 18, Vite, Tailwind CSS, Zustand, TanStack Query v5 |
| Auth | JWT con refresh tokens |
| PDF | WeasyPrint |
| Infraestructura | Docker + Docker Compose |

No sugerir alternativas a este stack salvo que haya un bloqueo técnico justificado.

---

## Módulos del sistema

### Fase 1 – MVP

| # | Módulo | Descripción |
|---|---|---|
| 1 | **Clientes** | Ficha, datos de contacto, historial de obras y facturas, documentación adjunta |
| 2 | **Visitas Técnicas** | Visita previa a la obra: notas, materiales estimados, fotos, croquis. Punto de origen del presupuesto |
| 3 | **Presupuestos** | Generado desde visita. Líneas tipadas, margen interno, versiones, PDF, conversión a obra |
| 4 | **Obras** | Ciclo completo: creada desde presupuesto aceptado → ejecución → cierre |
| 4a | **Tareas de obra** | Trabajos a realizar dentro de una obra, con estado y control de materiales |
| 4b | **Materiales de tarea** | Material previsto vs consumido por tarea, vinculado al inventario en tiempo real |
| 5 | **Facturación** | Facturas vinculadas a obra y presupuesto, control de pagos, exportación a PDF |
| 6 | **Inventario** | Materiales y herramientas, stock mínimo, alertas de reposición, entradas/salidas por obra |
| 7 | **Proveedores** | Ficha, condiciones comerciales, materiales asociados, historial de compras |
| 8 | **Dashboard** | Métricas clave: obras activas, facturación del mes, cobros pendientes, stock bajo mínimos, presupuestos sin respuesta |

### Fase 2 – Gestión de equipo (modelo de datos preparado desde Fase 1)

| # | Módulo | Descripción |
|---|---|---|
| 9 | **Operarios** | Ficha, especialidad, disponibilidad |
| 10 | **Partes de trabajo** | Horas trabajadas por tarea y operario |
| 11 | **Calendario** | Planificación visual de obras y asignación de equipo |

---

## Flujo principal del sistema

```
Cliente
  └─→ Visita Técnica
           │  notas técnicas, fotos, materiales estimados
           └─→ Presupuesto (borrador)
                    │  líneas: labor | material | other
                    │  margen interno por línea y total
                    │  versiones si el cliente pide cambios
                    │  export PDF → envío al cliente
                    ├─→ [rechazado] → cerrado, queda registrado
                    └─→ [aceptado]
                              └─→ Obra (automática)
                                       │  BudgetLine(labor)    → Task
                                       │  BudgetLine(material) → TaskMaterial
                                       └─→ Tareas + Materiales
                                                └─→ Factura → Cobro ✓
```

---

## Modelo de datos — Entidades y relaciones

```
Customer
 ├── SiteVisit (1..N)
 │    ├── site_visit_id, customer_id, address
 │    ├── visit_date, status: scheduled|completed|cancelled
 │    ├── description, work_scope, technical_notes
 │    ├── estimated_duration
 │    ├── SiteVisitMaterial (1..N)
 │    │    ├── material_id → InventoryItem (nullable)
 │    │    ├── description (libre si no está en inventario)
 │    │    └── estimated_qty
 │    ├── SiteVisitDocument (1..N)
 │    └── Budget (1..N)
 │         ├── budget_id, budget_number (PRES-YYYY-NNNN)
 │         ├── status: draft|sent|accepted|rejected|expired
 │         ├── version (integer, empieza en 1)
 │         ├── issue_date, valid_until
 │         ├── tax_rate, discount
 │         ├── work_order_id → WorkOrder (nullable)
 │         └── BudgetLine (1..N)
 │              ├── line_type: labor | material | other
 │              ├── description
 │              ├── material_id → InventoryItem (nullable)
 │              ├── quantity, unit_price (venta), unit_cost (interno)
 │              └── subtotal (calculado)
 └── WorkOrder (1..N)
      ├── work_order_id, customer_id
      ├── origin_budget_id → Budget
      ├── assigned_to → Operator (nullable, Fase 2)
      ├── status: draft|in_progress|pending_closure|closed
      ├── Task (1..N)
      │    ├── status: pending|in_progress|completed
      │    ├── estimated_hours, actual_hours
      │    └── TaskMaterial (1..N)
      │         ├── material_id → InventoryItem
      │         ├── estimated_quantity
      │         ├── consumed_quantity
      │         └── unit_cost (precio en momento de consumo)
      └── Invoice (1..N)
           ├── origin_budget_id → Budget
           └── status: draft|sent|paid|overdue

InventoryItem
 ├── supplier_id → Supplier
 └── StockMovement (1..N)  [entry | exit, vinculado a obra]

Supplier
 └── InventoryItem (1..N)
```

---

## Reglas de negocio clave

```
stock_available    = stock_current - SUM(estimated_quantity
                     WHERE task.status IN ['pending','in_progress'])

work_order_cost    = SUM(consumed_quantity × unit_cost)
                     FROM task_materials JOIN tasks
                     WHERE work_order_id = ?

budget_margin      = (unit_price - unit_cost) / unit_price
                     por línea y agregado en total del presupuesto
                     → solo visible internamente, nunca en el PDF del cliente

work_order_status  → 'pending_closure'
                     WHEN ALL tasks.status = 'completed'

budget → work_order conversion:
  BudgetLine(labor)    → Task(name, estimated_hours)
  BudgetLine(material) → Task + TaskMaterial(estimated_quantity, unit_cost)
  BudgetLine(other)    → WorkOrder.notes (sin conversión estructural)
```

---

## Arquitectura del código

### Estructura de capas (backend)

```
routers → services → repositories → models
```

Nunca poner lógica de negocio en los routers. Nunca acceder a la base de datos desde los servicios directamente; usar siempre el repositorio.

### Estructura de carpetas (backend)

```
app/
├── api/
│   └── v1/
│       └── routers/        # Un archivo por módulo
├── services/               # Lógica de negocio
├── repositories/           # Acceso a datos
├── models/                 # Modelos SQLAlchemy
├── schemas/                # Schemas Pydantic v2
├── core/                   # Config, seguridad, DB session
└── migrations/             # Alembic
```

### Estructura de carpetas (frontend)

```
src/
├── features/               # Un directorio por módulo
│   ├── customers/
│   ├── site-visits/
│   ├── budgets/
│   ├── work-orders/
│   ├── invoicing/
│   ├── inventory/
│   ├── suppliers/
│   └── dashboard/
├── shared/
│   ├── components/
│   ├── hooks/
│   └── utils/
└── lib/                    # Clientes HTTP, configuración
```

---

## Estado de módulos

### Fase 1 – MVP

| Módulo | Estado | Notas |
|---|---|---|
| Clientes | ⬜ Pendiente | |
| Visitas Técnicas | ✅ Completado | |
| Presupuestos | ⬜ Pendiente | Incluye versiones y margen interno |
| Obras + Tasks + TaskMaterials | ⬜ Pendiente | Core del sistema |
| Facturación | ⬜ Pendiente | |
| Inventario | ⬜ Pendiente | |
| Proveedores | ✅ Completado | |
| Dashboard | ⬜ Pendiente | |

### Fase 2 – Gestión de equipo

| Módulo | Estado | Notas |
|---|---|---|
| Operarios | ⬜ Diferido | FK preparada en WorkOrder desde Fase 1 |
| Partes de trabajo | ⬜ Diferido | |
| Calendario | ⬜ Diferido | |

> **Leyenda:** ⬜ Pendiente · 🔄 En progreso · ✅ Completado

---

## Convenciones de nomenclatura

- **Todo el código en inglés**: variables, funciones, clases, métodos, constantes, parámetros, nombres de archivos
- Archivos y carpetas Python: `snake_case`
- Archivos y carpetas frontend: `kebab-case`
- Componentes React: `PascalCase`
- Comentarios y docstrings: siempre en inglés
- Mensajes de error al usuario final: en español
- Logs internos: en inglés
- Comunicación en la conversación: en español
- UI del frontend: en español

### Ejemplos correctos

```python
# ✅ Python
def get_site_visit_by_id(visit_id: UUID) -> SiteVisitResponse: ...
budget_status = BudgetStatus.ACCEPTED
```

```typescript
// ✅ TypeScript / React
const budgetLineList = useBudgetStore()
const convertBudgetToWorkOrder = async (budgetId: string) => { ... }
```

### Ejemplos incorrectos

```python
# ❌
def obtener_visita_por_id(id_visita: UUID): ...
estado_presupuesto = EstadoPresupuesto.ACEPTADO
```

---

## Estándares de código

### Backend

- Modelos SQLAlchemy con sintaxis 2.0: `Mapped[]` y `mapped_column()`
- Schemas con Pydantic v2
- IDs: UUID v4 (nunca enteros autoincrementales)
- Toda tabla lleva `created_at` y `updated_at` con timezone
- Proporcionar siempre la migración Alembic junto con el modelo
- Manejo de errores con HTTPException y códigos semánticos

### Frontend

- Componentes funcionales con hooks únicamente (nada de clases)
- Estado global con Zustand; sin Redux
- Llamadas al servidor con TanStack Query v5
- TypeScript estricto en todo el frontend

---

## Decisiones de arquitectura tomadas

| Decisión | Elección | Razón |
|---|---|---|
| Arquitectura | Monolito modular | Escala 1–10 usuarios, sin necesidad de microservicios |
| IDs | UUID v4 | Evita exposición de secuencias, facilita sincronización futura |
| Estado frontend | Zustand | Suficiente para la escala, sin boilerplate de Redux |
| ORM | SQLAlchemy async 2.0 | Rendimiento async, tipado moderno con `Mapped[]` |
| Migraciones | Alembic | Estándar del ecosistema FastAPI/SQLAlchemy |
| Presupuesto | Módulo separado de Facturación | Presupuestar es vender; facturar es cobrar. Ciclos de vida distintos |
| Visita Técnica | Módulo propio, origen del presupuesto | Digitaliza el trabajo de campo y evita pérdida de información |
| Margen en presupuesto | Solo visible internamente | Nunca expuesto en PDF ni en vistas de cliente |

---

## Compatibilidad Fase 1 → Fase 2

Las siguientes decisiones garantizan que la transición sea aditiva:

- `WorkOrder` incluye `assigned_to UUID NULL` (FK a `operators`) desde el inicio
- `Task` incluye `estimated_hours` y `actual_hours` desde el inicio
- No hay lógica que asuma usuario único; el sistema está multi-usuario desde el arranque
- Las migraciones de Fase 2 solo añaden tablas (`operators`, `work_logs`) y activan la FK ya existente

---

## Restricciones de diseño

- Escala objetivo: 2–10 usuarios concurrentes → no sobrediseñar
- Monolito modular: sin microservicios
- El modelo de datos debe ser compatible con Fase 2 desde el inicio
- Las migraciones entre Fase 1 y Fase 2 deben ser **aditivas**, nunca destructivas
- Sistema de uso interno: no es un SaaS público

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2025-01 | Definición inicial del proyecto y módulos base |
| 2025-01 | Añadido módulo Visitas Técnicas como origen del flujo comercial |
| 2025-01 | Separado Presupuestos de Facturación como módulo propio |
| 2025-01 | Añadidas reglas de conversión presupuesto → obra |
| 2025-01 | Añadido margen interno por línea de presupuesto |
| 2025-01 | Añadido soporte a versiones de presupuesto |
