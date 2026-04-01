import type { InvoiceEffectiveStatus } from '../types'

const STATUS_CONFIG: Record<
  InvoiceEffectiveStatus,
  { label: string; className: string }
> = {
  draft: {
    label: 'Borrador',
    className: 'bg-gray-100 text-gray-600',
  },
  sent: {
    label: 'Enviada',
    className: 'bg-blue-100 text-blue-700',
  },
  overdue: {
    label: 'Vencida',
    className: 'bg-red-100 text-red-700',
  },
  partially_paid: {
    label: 'Cobro parcial',
    className: 'bg-amber-100 text-amber-700',
  },
  paid: {
    label: 'Cobrada',
    className: 'bg-green-100 text-green-700',
  },
  cancelled: {
    label: 'Anulada',
    className: 'bg-gray-200 text-gray-500',
  },
}

interface Props {
  status: InvoiceEffectiveStatus
  size?: 'sm' | 'md'
}

export function InvoiceStatusBadge({ status, size = 'md' }: Props) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft
  const sizeClass = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-xs px-2 py-1'
  return (
    <span
      className={`inline-flex items-center rounded font-medium ${sizeClass} ${config.className}`}
    >
      {config.label}
    </span>
  )
}
