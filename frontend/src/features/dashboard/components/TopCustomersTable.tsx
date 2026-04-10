import { formatEur } from '../../../shared/utils/format'
import type { TopCustomer } from '../types'

interface Props {
  customers: TopCustomer[]
}

export function TopCustomersTable({ customers }: Props) {
  const max = customers[0]?.invoiced ?? 1

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Top clientes</h3>
      </div>

      {customers.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-6">Sin datos en el período</p>
      ) : (
        <div className="divide-y divide-gray-50">
          {customers.map((c, i) => (
            <div key={c.customer_id} className="px-4 py-2.5 flex items-center gap-3">
              <span className="text-xs font-bold text-gray-300 w-4 shrink-0">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-800 truncate">{c.customer_name}</p>
                <div className="mt-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-blue-400"
                    style={{ width: `${(c.invoiced / max) * 100}%` }}
                  />
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs font-semibold text-gray-700">{formatEur(c.invoiced)}</p>
                <p className="text-xs text-gray-400">{c.invoice_count} fact.</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
