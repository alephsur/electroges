import { formatEur } from '../../../shared/utils/format'
import type { TopDebtorCustomer } from '../types'

interface Props {
  debtors: TopDebtorCustomer[]
}

function OverdueBadge({ days }: { days: number }) {
  const color =
    days > 60
      ? 'bg-red-50 text-red-700'
      : days > 30
      ? 'bg-amber-50 text-amber-700'
      : 'bg-orange-50 text-orange-600'
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-semibold ${color}`}>
      {days.toFixed(0)}d
    </span>
  )
}

export function TopDebtorsTable({ debtors }: Props) {
  const maxOverdue = debtors[0]?.total_overdue ?? 1

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Clientes morosos</h3>
        <p className="text-xs text-gray-400 mt-0.5">Facturas vencidas sin cobrar</p>
      </div>

      {debtors.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-6">
          Sin facturas vencidas — ¡todo al día!
        </p>
      ) : (
        <div className="divide-y divide-gray-50">
          {debtors.map((d, i) => (
            <div key={d.customer_id} className="px-4 py-2.5 flex items-center gap-3">
              <span className="text-xs font-bold text-gray-300 w-4 shrink-0">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-800 truncate">{d.customer_name}</p>
                <div className="mt-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-red-400"
                    style={{ width: `${(d.total_overdue / maxOverdue) * 100}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="text-right">
                  <p className="text-xs font-semibold text-red-600">{formatEur(d.total_overdue)}</p>
                  <p className="text-xs text-gray-400">{d.invoice_count} fact.</p>
                </div>
                <OverdueBadge days={d.avg_days_overdue} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
