import dayjs from 'dayjs'
import 'dayjs/locale/es'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { RecentActivityItem } from '../types'

dayjs.extend(relativeTime)
dayjs.locale('es')

// ── Labels & styles ───────────────────────────────────────────────────────────

const ENTITY_LABELS: Record<RecentActivityItem['entity_type'], string> = {
  invoice:        'Factura',
  work_order:     'Obra',
  budget:         'Presupuesto',
  site_visit:     'Visita',
  purchase_order: 'Pedido',
}

const ENTITY_COLORS: Record<RecentActivityItem['entity_type'], string> = {
  invoice:        'bg-blue-100 text-blue-700',
  work_order:     'bg-orange-100 text-orange-700',
  budget:         'bg-purple-100 text-purple-700',
  site_visit:     'bg-teal-100 text-teal-700',
  purchase_order: 'bg-yellow-100 text-yellow-700',
}

const ENTITY_DOT: Record<RecentActivityItem['entity_type'], string> = {
  invoice:        'bg-blue-400',
  work_order:     'bg-orange-400',
  budget:         'bg-purple-400',
  site_visit:     'bg-teal-400',
  purchase_order: 'bg-yellow-400',
}

const STATUS_LABELS: Record<string, string> = {
  draft:           'Borrador',
  sent:            'Enviado',
  accepted:        'Aceptado',
  rejected:        'Rechazado',
  expired:         'Caducado',
  paid:            'Cobrada',
  cancelled:       'Anulada',
  active:          'Activa',
  pending_closure: 'Pend. cierre',
  closed:          'Cerrada',
  scheduled:       'Programada',
  in_progress:     'En curso',
  completed:       'Completada',
  no_show:         'No presentado',
  pending:         'Pendiente',
  received:        'Recibido',
}

interface Props {
  items: RecentActivityItem[]
}

export function RecentActivityFeed({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-xs text-gray-400">
        Sin actividad reciente
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-50">
      {items.map((item) => (
        <div key={`${item.entity_type}-${item.id}`} className="flex items-center gap-3 px-4 py-2.5">
          {/* Type badge */}
          <span
            className={`shrink-0 rounded-md px-1.5 py-0.5 text-xs font-semibold ${ENTITY_COLORS[item.entity_type]}`}
          >
            {ENTITY_LABELS[item.entity_type]}
          </span>

          {/* Number + customer */}
          <div className="flex-1 min-w-0">
            <span className="text-xs font-medium text-gray-800">{item.entity_number}</span>
            {item.customer_name && (
              <span className="text-xs text-gray-400 ml-1.5">· {item.customer_name}</span>
            )}
          </div>

          {/* Status dot + label */}
          <div className="flex items-center gap-1 shrink-0">
            <span className={`w-1.5 h-1.5 rounded-full ${ENTITY_DOT[item.entity_type]}`} />
            <span className="text-xs text-gray-500">
              {STATUS_LABELS[item.status] ?? item.status}
            </span>
          </div>

          {/* Relative time */}
          <span className="text-xs text-gray-300 shrink-0 w-16 text-right">
            {dayjs(item.date).fromNow(true)}
          </span>
        </div>
      ))}
    </div>
  )
}
