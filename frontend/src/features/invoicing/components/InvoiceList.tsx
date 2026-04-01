import { FileText } from 'lucide-react'
import { InvoiceStatusBadge } from './InvoiceStatusBadge'
import { PaymentProgressBar } from './PaymentProgressBar'
import type { InvoiceSummary } from '../types'

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('es-ES')
}

interface Props {
  invoices: InvoiceSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  isLoading?: boolean
}

export function InvoiceList({
  invoices,
  selectedId,
  onSelect,
  isLoading,
}: Props) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 p-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg bg-gray-100"
          />
        ))}
      </div>
    )
  }

  if (invoices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-gray-400">
        <FileText size={32} />
        <p className="text-sm">No hay facturas</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-100">
      {invoices.map((inv) => (
        <button
          key={inv.id}
          onClick={() => onSelect(inv.id)}
          className={`w-full p-3 text-left transition-colors hover:bg-gray-50 ${
            selectedId === inv.id ? 'bg-blue-50' : ''
          }`}
        >
          {/* Row 1: number + status */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 min-w-0">
              {inv.is_rectification && (
                <span className="shrink-0 rounded bg-red-100 px-1 py-0.5 text-xs font-bold text-red-700">
                  RECT.
                </span>
              )}
              <span className="truncate text-sm font-semibold text-gray-800">
                {inv.invoice_number}
              </span>
            </div>
            <InvoiceStatusBadge status={inv.effective_status} size="sm" />
          </div>

          {/* Row 2: customer + work order */}
          <div className="mt-0.5 text-xs text-gray-700 truncate">
            {inv.customer_name}
          </div>
          {inv.work_order_number && (
            <div className="text-xs text-gray-400 truncate">
              Obra {inv.work_order_number}
            </div>
          )}

          {/* Row 3: due date */}
          <div className="mt-1 flex items-center justify-between text-xs">
            <span
              className={`${
                inv.effective_status === 'overdue'
                  ? 'font-medium text-red-600'
                  : 'text-gray-500'
              }`}
            >
              Vence {fmtDate(inv.due_date)}
              {inv.days_overdue > 0 &&
                ` · ${inv.days_overdue}d vencida`}
            </span>
            <span className="font-medium text-gray-800">
              {fmt(inv.total)} €
            </span>
          </div>

          {/* Row 4: payment progress */}
          <div className="mt-1.5">
            <PaymentProgressBar
              total={inv.total}
              total_paid={inv.total_paid}
              pending_amount={inv.pending_amount}
              effective_status={inv.effective_status}
              showLabels={false}
            />
          </div>
        </button>
      ))}
    </div>
  )
}
