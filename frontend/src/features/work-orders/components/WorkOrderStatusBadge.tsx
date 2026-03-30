import type { WorkOrderStatus } from '../types'

const STATUS_CONFIG: Record<
  WorkOrderStatus,
  { label: string; className: string }
> = {
  draft: {
    label: 'Borrador',
    className: 'bg-gray-100 text-gray-700',
  },
  active: {
    label: 'En ejecución',
    className: 'bg-blue-100 text-blue-700',
  },
  pending_closure: {
    label: 'Pendiente cierre',
    className: 'bg-amber-100 text-amber-700',
  },
  closed: {
    label: 'Cerrada',
    className: 'bg-green-100 text-green-700',
  },
  cancelled: {
    label: 'Cancelada',
    className: 'bg-red-100 text-red-700',
  },
}

interface WorkOrderStatusBadgeProps {
  status: WorkOrderStatus
}

export function WorkOrderStatusBadge({ status }: WorkOrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    className: 'bg-gray-100 text-gray-600',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  )
}
