import type { SiteVisitStatus } from '../types'

const STATUS_CONFIG: Record<SiteVisitStatus, { label: string; className: string }> = {
  scheduled: {
    label: 'Planificada',
    className: 'bg-blue-100 text-blue-700',
  },
  in_progress: {
    label: 'En curso',
    className: 'bg-amber-100 text-amber-700',
  },
  completed: {
    label: 'Completada',
    className: 'bg-green-100 text-green-700',
  },
  cancelled: {
    label: 'Cancelada',
    className: 'bg-gray-100 text-gray-600',
  },
  no_show: {
    label: 'No presentado',
    className: 'bg-red-100 text-red-700',
  },
}

interface SiteVisitStatusBadgeProps {
  status: SiteVisitStatus
  className?: string
}

export function SiteVisitStatusBadge({ status, className = '' }: SiteVisitStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, className: 'bg-gray-100 text-gray-600' }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className} ${className}`}
    >
      {config.label}
    </span>
  )
}
