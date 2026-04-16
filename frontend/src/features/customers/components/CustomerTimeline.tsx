import { Clock, FileText, Briefcase, Receipt, MapPin } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useCustomerTimeline } from '../hooks/use-customers'
import type { TimelineEvent, TimelineEventType } from '../types'

const EVENT_CONFIG: Record<
  TimelineEventType,
  { icon: React.ReactNode; colorClass: string; groupColor: string }
> = {
  site_visit: {
    icon: <MapPin size={14} />,
    colorClass: 'bg-blue-100 text-blue-600',
    groupColor: 'border-blue-200',
  },
  budget_created: {
    icon: <FileText size={14} />,
    colorClass: 'bg-amber-100 text-amber-600',
    groupColor: 'border-amber-200',
  },
  budget_sent: {
    icon: <FileText size={14} />,
    colorClass: 'bg-amber-100 text-amber-600',
    groupColor: 'border-amber-200',
  },
  budget_accepted: {
    icon: <FileText size={14} />,
    colorClass: 'bg-amber-100 text-amber-600',
    groupColor: 'border-amber-200',
  },
  budget_rejected: {
    icon: <FileText size={14} />,
    colorClass: 'bg-amber-100 text-amber-600',
    groupColor: 'border-amber-200',
  },
  work_order_created: {
    icon: <Briefcase size={14} />,
    colorClass: 'bg-green-100 text-green-600',
    groupColor: 'border-green-200',
  },
  work_order_closed: {
    icon: <Briefcase size={14} />,
    colorClass: 'bg-green-100 text-green-600',
    groupColor: 'border-green-200',
  },
  invoice_issued: {
    icon: <Receipt size={14} />,
    colorClass: 'bg-emerald-100 text-emerald-700',
    groupColor: 'border-emerald-200',
  },
  invoice_paid: {
    icon: <Receipt size={14} />,
    colorClass: 'bg-emerald-100 text-emerald-700',
    groupColor: 'border-emerald-200',
  },
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'hoy'
  if (diffDays === 1) return 'hace 1 día'
  if (diffDays < 30) return `hace ${diffDays} días`
  if (diffDays < 365) return `hace ${Math.floor(diffDays / 30)} meses`
  return `hace ${Math.floor(diffDays / 365)} años`
}

function formatMonthYear(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })
}

function groupEventsByMonth(events: TimelineEvent[]): Map<string, TimelineEvent[]> {
  const groups = new Map<string, TimelineEvent[]>()
  for (const event of events) {
    const key = formatMonthYear(event.event_date)
    const group = groups.get(key) ?? []
    group.push(event)
    groups.set(key, group)
  }
  return groups
}

const REFERENCE_ROUTES: Record<string, (id: string) => string> = {
  site_visit: (id) => `/visitas/${id}`,
  budget: (id) => `/presupuestos/${id}`,
  work_order: (id) => `/obras/${id}`,
  invoice: (id) => `/facturacion/${id}`,
}

interface CustomerTimelineProps {
  customerId: string
}

export function CustomerTimeline({ customerId }: CustomerTimelineProps) {
  const navigate = useNavigate()
  const { data, isLoading } = useCustomerTimeline(customerId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-400">
        <span className="text-sm">Cargando actividad...</span>
      </div>
    )
  }

  if (!data || data.events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-gray-400">
        <Clock size={36} className="mb-3 text-gray-300" />
        <p className="font-medium text-gray-500">Sin actividad registrada</p>
        <p className="text-sm mt-1 max-w-xs">
          Los presupuestos, obras y facturas de este cliente aparecerán aquí cuando estén
          disponibles.
        </p>
      </div>
    )
  }

  const groups = groupEventsByMonth(data.events)

  return (
    <div className="space-y-5">
      {/* Summary metrics strip */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-lg bg-blue-50 px-3 py-2 text-center">
          <p className="text-lg font-semibold text-blue-700">{data.total_site_visits}</p>
          <p className="text-xs text-blue-500">Visitas</p>
        </div>
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-center">
          <p className="text-lg font-semibold text-amber-700">{data.total_budgets}</p>
          <p className="text-xs text-amber-500">Presupuestos</p>
        </div>
        <div className="rounded-lg bg-green-50 px-3 py-2 text-center">
          <p className="text-lg font-semibold text-green-700">{data.total_work_orders}</p>
          <p className="text-xs text-green-500">Obras</p>
        </div>
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-center">
          <p className="text-lg font-semibold text-emerald-700">
            {data.total_invoiced.toLocaleString('es-ES', {
              style: 'currency',
              currency: 'EUR',
              maximumFractionDigits: 0,
            })}
          </p>
          <p className="text-xs text-emerald-500">Facturado</p>
        </div>
      </div>

      {/* Timeline events grouped by month */}
      {Array.from(groups.entries()).map(([month, events]) => (
        <div key={month}>
          {/* Month separator */}
          <div className="flex items-center gap-3 mb-3">
            <div className="h-px flex-1 bg-gray-100" />
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
              {month}
            </span>
            <div className="h-px flex-1 bg-gray-100" />
          </div>

          {/* Events */}
          <div className="relative pl-6">
            {/* Vertical line */}
            <div className="absolute left-2 top-0 bottom-0 w-px bg-gray-100" />

            <div className="space-y-4">
              {events.map((event, idx) => {
                const config = EVENT_CONFIG[event.event_type]
                const detailRoute = REFERENCE_ROUTES[event.reference_type]?.(event.reference_id)
                return (
                  <div key={`${event.reference_id}-${idx}`} className="relative flex gap-3">
                    {/* Dot */}
                    <div
                      className={`absolute -left-4 mt-0.5 flex h-5 w-5 items-center justify-center rounded-full ${config.colorClass}`}
                    >
                      {config.icon}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{event.title}</p>
                          {event.subtitle && (
                            <p className="text-xs text-gray-500 mt-0.5">{event.subtitle}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {event.amount != null && event.amount > 0 && (
                            <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                              {event.amount.toLocaleString('es-ES', {
                                style: 'currency',
                                currency: 'EUR',
                              })}
                            </span>
                          )}
                          <span
                            className="text-xs text-gray-400"
                            title={new Date(event.event_date).toLocaleDateString('es-ES')}
                          >
                            {formatRelativeDate(event.event_date)}
                          </span>
                        </div>
                      </div>
                      {detailRoute && (
                        <button
                          onClick={() => navigate(detailRoute)}
                          className="mt-1 text-xs text-brand-600 hover:text-brand-700 hover:underline"
                        >
                          Ver detalle →
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
