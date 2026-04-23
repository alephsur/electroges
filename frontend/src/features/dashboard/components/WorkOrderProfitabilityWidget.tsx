import { formatEur } from '../../../shared/utils/format'
import type { WorkOrderProfitabilityItem } from '../types'

interface Props {
  items: WorkOrderProfitabilityItem[]
}

function MarginBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-xs text-gray-400">—</span>
  const color =
    value >= 40
      ? 'bg-emerald-50 text-emerald-700'
      : value >= 20
      ? 'bg-amber-50 text-amber-700'
      : 'bg-red-50 text-red-700'
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-semibold ${color}`}>
      {value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

function CompareBar({
  budgeted,
  actual,
  formatFn,
}: {
  budgeted: number
  actual: number
  formatFn: (v: number) => string
}) {
  const max = Math.max(budgeted, actual, 0.01)
  const overrun = actual > budgeted

  return (
    <div className="space-y-0.5">
      <div className="flex items-center gap-1.5">
        <div className="w-16 h-1.5 rounded-full bg-gray-100 overflow-hidden flex-shrink-0">
          <div
            className="h-full rounded-full bg-blue-400"
            style={{ width: `${(budgeted / max) * 100}%` }}
          />
        </div>
        <span className="text-xs text-gray-500">{formatFn(budgeted)}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-16 h-1.5 rounded-full bg-gray-100 overflow-hidden flex-shrink-0">
          <div
            className={`h-full rounded-full ${overrun ? 'bg-red-400' : 'bg-emerald-400'}`}
            style={{ width: `${Math.min((actual / max) * 100, 100)}%` }}
          />
        </div>
        <span className={`text-xs font-medium ${overrun ? 'text-red-600' : 'text-gray-700'}`}>
          {formatFn(actual)}
        </span>
      </div>
    </div>
  )
}

function RevenuePill({
  budgeted,
  certified,
  revenueBase,
}: {
  budgeted: number
  certified: number
  revenueBase: number
}) {
  const hasCertified = certified > 0
  const deviated = hasCertified && Math.abs(certified - budgeted) > 0.01

  return (
    <div className="text-right">
      {hasCertified ? (
        <>
          <p className="font-semibold text-gray-800">{formatEur(certified)}</p>
          <p className="text-gray-400 line-through text-xs">{formatEur(budgeted)}</p>
        </>
      ) : (
        <>
          <p className="font-medium text-gray-700">{formatEur(budgeted)}</p>
          <p className="text-xs text-gray-400">sin certificar</p>
        </>
      )}
      {deviated && (
        <span
          className={`text-xs font-medium ${
            certified > budgeted ? 'text-emerald-600' : 'text-amber-600'
          }`}
        >
          {certified > budgeted ? '+' : ''}
          {formatEur(certified - budgeted)}
        </span>
      )}
    </div>
  )
}

export function WorkOrderProfitabilityWidget({ items }: Props) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">
            Rentabilidad por obra cerrada
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Horas/material: presupuestado (azul) vs real · Margen sobre ingresos certificados
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400" />
            Presup.
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
            Real
          </span>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-6">
          Sin obras cerradas registradas
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-50">
                <th className="px-4 py-2 text-left font-medium text-gray-400 whitespace-nowrap">
                  Obra
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-400 whitespace-nowrap">
                  Horas
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-400 whitespace-nowrap">
                  Material
                </th>
                <th className="px-4 py-2 text-right font-medium text-gray-400 whitespace-nowrap">
                  Ingresos
                </th>
                <th className="px-4 py-2 text-right font-medium text-gray-400 whitespace-nowrap">
                  Margen
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => (
                <tr key={item.work_order_id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-gray-800">{item.work_order_number}</p>
                    <p className="text-gray-400 truncate max-w-[120px]">{item.customer_name}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    <CompareBar
                      budgeted={item.budgeted_hours}
                      actual={item.actual_hours}
                      formatFn={(v) => `${v.toFixed(1)}h`}
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <CompareBar
                      budgeted={item.budgeted_material_cost}
                      actual={item.actual_material_cost}
                      formatFn={formatEur}
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <RevenuePill
                      budgeted={item.budgeted_revenue}
                      certified={item.total_certified}
                      revenueBase={item.revenue_base}
                    />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <MarginBadge value={item.margin_pct} />
                    <p className="text-xs text-gray-400 mt-0.5">
                      {item.total_certified > 0 ? 'certif.' : 'presup.'}
                    </p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
