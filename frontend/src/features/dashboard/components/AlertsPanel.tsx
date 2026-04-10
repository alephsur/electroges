import { AlertTriangle, Clock } from 'lucide-react'
import { formatEur } from '../../../shared/utils/format'
import type { OverdueInvoiceItem, PendingBudgetItem } from '../types'

interface Props {
  overdueInvoices: OverdueInvoiceItem[]
  pendingBudgets: PendingBudgetItem[]
}

export function AlertsPanel({ overdueInvoices, pendingBudgets }: Props) {
  const hasAlerts = overdueInvoices.length > 0 || pendingBudgets.length > 0

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Alertas</h3>
      </div>

      {!hasAlerts && (
        <p className="text-xs text-gray-400 text-center py-6">Sin alertas pendientes</p>
      )}

      {overdueInvoices.length > 0 && (
        <div className="p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle size={12} className="text-red-500" />
            <span className="text-xs font-medium text-red-600">
              Facturas vencidas ({overdueInvoices.length})
            </span>
          </div>
          <div className="space-y-1.5">
            {overdueInvoices.slice(0, 5).map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between rounded-lg bg-red-50 px-2.5 py-2"
              >
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{inv.customer_name}</p>
                  <p className="text-xs text-gray-400">{inv.invoice_number} · {inv.days_overdue}d vencida</p>
                </div>
                <span className="text-xs font-semibold text-red-600 shrink-0 ml-2">
                  {formatEur(inv.pending_amount)}
                </span>
              </div>
            ))}
            {overdueInvoices.length > 5 && (
              <p className="text-xs text-gray-400 text-center pt-1">
                +{overdueInvoices.length - 5} más
              </p>
            )}
          </div>
        </div>
      )}

      {pendingBudgets.length > 0 && (
        <div className={`p-3 ${overdueInvoices.length > 0 ? 'border-t border-gray-100' : ''}`}>
          <div className="flex items-center gap-1.5 mb-2">
            <Clock size={12} className="text-amber-500" />
            <span className="text-xs font-medium text-amber-600">
              Presupuestos sin respuesta ({pendingBudgets.length})
            </span>
          </div>
          <div className="space-y-1.5">
            {pendingBudgets.slice(0, 5).map((b) => (
              <div
                key={b.id}
                className="flex items-center justify-between rounded-lg bg-amber-50 px-2.5 py-2"
              >
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{b.customer_name}</p>
                  <p className="text-xs text-gray-400">{b.budget_number} · {b.days_since_sent}d enviado</p>
                </div>
                <span className="text-xs font-semibold text-amber-700 shrink-0 ml-2">
                  {formatEur(b.total)}
                </span>
              </div>
            ))}
            {pendingBudgets.length > 5 && (
              <p className="text-xs text-gray-400 text-center pt-1">
                +{pendingBudgets.length - 5} más
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
