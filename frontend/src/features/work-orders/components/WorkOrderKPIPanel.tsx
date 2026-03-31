import type { WorkOrderKPIs } from '../types'

function fmt(n: number | string, decimals = 2) {
  return Number(n).toLocaleString('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function DeviationIndicator({ pct }: { pct: number }) {
  const abs = Math.abs(pct)
  if (abs <= 5) return <span className="text-green-600 text-xs">±{fmt(abs, 1)}%</span>
  if (pct > 0)
    return <span className="text-red-600 text-xs">+{fmt(abs, 1)}%</span>
  return <span className="text-green-600 text-xs">-{fmt(abs, 1)}%</span>
}

function MarginSemaphore({ pct }: { pct: number }) {
  let color = 'text-red-600'
  if (pct >= 25) color = 'text-green-600'
  else if (pct >= 15) color = 'text-amber-600'
  return <span className={`text-lg font-bold ${color}`}>{fmt(pct, 1)}%</span>
}

interface WorkOrderKPIPanelProps {
  kpis: WorkOrderKPIs
}

export function WorkOrderKPIPanel({ kpis }: WorkOrderKPIPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {/* Progreso */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Progreso
        </p>
        <div className="mt-2 flex items-end gap-2">
          <span className="text-2xl font-bold text-gray-900">
            {fmt(kpis.progress_pct, 1)}%
          </span>
          <span className="mb-0.5 text-sm text-gray-500">
            {kpis.completed_tasks}/{kpis.total_tasks} tareas
          </span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-blue-500 transition-all"
            style={{ width: `${Math.min(kpis.progress_pct, 100)}%` }}
          />
        </div>
      </div>

      {/* Horas */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Horas
        </p>
        <div className="mt-2 flex items-end gap-2">
          <span className="text-2xl font-bold text-gray-900">
            {fmt(kpis.actual_hours, 1)}h
          </span>
          <span className="mb-0.5 text-sm text-gray-500">
            / {fmt(kpis.estimated_hours, 1)}h est.
          </span>
        </div>
        <div className="mt-1">
          <DeviationIndicator pct={kpis.hours_deviation_pct} />
          <span className="ml-1 text-xs text-gray-400">desviación</span>
        </div>
      </div>

      {/* Costes */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Coste real
        </p>
        <div className="mt-2 flex items-end gap-2">
          <span className="text-2xl font-bold text-gray-900">
            {fmt(kpis.actual_cost)}€
          </span>
          <span className="mb-0.5 text-sm text-gray-500">
            / {fmt(kpis.budget_cost)}€ pres.
          </span>
        </div>
        <div className="mt-1">
          <DeviationIndicator pct={kpis.cost_deviation_pct} />
          <span className="ml-1 text-xs text-gray-400">desviación</span>
        </div>
      </div>

      {/* Facturación */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Facturación
        </p>
        <div className="mt-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Presupuestado</span>
            <span className="font-medium">{fmt(kpis.budget_total)}€</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Certificado</span>
            <span className="font-medium text-blue-600">
              {fmt(kpis.total_certified)}€
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Pendiente</span>
            <span className="font-medium text-amber-600">
              {fmt(kpis.pending_to_certify)}€
            </span>
          </div>
        </div>
      </div>

      {/* Materiales */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Materiales
        </p>
        <div className="mt-2 flex items-end gap-2">
          <span className="text-2xl font-bold text-gray-900">
            {kpis.fully_consumed_materials}
          </span>
          <span className="mb-0.5 text-sm text-gray-500">
            / {kpis.total_task_materials} consumidos
          </span>
        </div>
        {kpis.pending_materials > 0 && (
          <p className="mt-1 text-xs text-amber-600">
            {kpis.pending_materials} pendiente
            {kpis.pending_materials !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Margen real */}
      <div className="rounded-xl border border-gray-100 bg-white p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Margen real
        </p>
        <div className="mt-2">
          <MarginSemaphore pct={kpis.margin_real_pct} />
        </div>
        <p className="mt-1 text-xs text-gray-400">
          {kpis.total_purchase_orders} pedido
          {kpis.total_purchase_orders !== 1 ? 's' : ''} vinculado
          {kpis.total_purchase_orders !== 1 ? 's' : ''}
          {kpis.pending_purchase_orders > 0 && (
            <span className="ml-1 text-amber-600">
              ({kpis.pending_purchase_orders} pendiente
              {kpis.pending_purchase_orders !== 1 ? 's' : ''})
            </span>
          )}
        </p>
      </div>
    </div>
  )
}
