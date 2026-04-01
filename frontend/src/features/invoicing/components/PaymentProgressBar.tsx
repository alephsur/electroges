import type { InvoiceEffectiveStatus } from '../types'

interface Props {
  total: number
  total_paid: number
  pending_amount: number
  effective_status: InvoiceEffectiveStatus
  showLabels?: boolean
}

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

export function PaymentProgressBar({
  total,
  total_paid,
  pending_amount,
  effective_status,
  showLabels = true,
}: Props) {
  const pct = total > 0 ? Math.min((total_paid / total) * 100, 100) : 0
  const isOverdue = effective_status === 'overdue'

  return (
    <div className="space-y-1">
      {/* Bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        {pct > 0 && (
          <div
            className="h-full rounded-full bg-green-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs text-gray-500">
          <span className="text-green-600 font-medium">
            {fmt(total_paid)} € cobrado
          </span>
          <span className={isOverdue ? 'text-red-600 font-medium' : ''}>
            {fmt(pending_amount)} € pendiente
          </span>
        </div>
      )}
    </div>
  )
}
