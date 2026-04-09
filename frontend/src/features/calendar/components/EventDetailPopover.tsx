import { useNavigate } from 'react-router-dom'
import { X, ExternalLink, Pencil } from 'lucide-react'
import type { CalendarAggregatedEvent } from '../types'

const TYPE_LABELS: Record<string, string> = {
  site_visit: 'Visita técnica',
  budget: 'Presupuesto',
  work_order: 'Obra',
  custom: 'Evento personalizado',
}

interface Props {
  event: CalendarAggregatedEvent
  onClose: () => void
  onEdit: () => void
}

export function EventDetailPopover({ event, onClose, onEdit }: Props) {
  const navigate = useNavigate()

  const formatDate = (iso: string) => {
    const d = iso.slice(0, 10)
    const [y, m, day] = d.split('-')
    return `${day}/${m}/${y}`
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Color bar */}
        <div
          className="h-2 rounded-t-xl"
          style={{ backgroundColor: event.color }}
        />

        <div className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 mb-3">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: event.color }}>
                {TYPE_LABELS[event.event_type] ?? event.event_type}
              </span>
              <h3 className="text-sm font-semibold text-gray-900 mt-0.5">{event.title}</h3>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 shrink-0">
              <X size={16} />
            </button>
          </div>

          {/* Dates */}
          <div className="text-xs text-gray-500 mb-2">
            {formatDate(event.start)}
            {event.end && event.end.slice(0, 10) !== event.start.slice(0, 10) && (
              <> → {formatDate(event.end)}</>
            )}
          </div>

          {/* Description */}
          {event.description && (
            <p className="text-sm text-gray-600 mb-3">{event.description}</p>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t border-gray-100">
            {event.event_type === 'custom' && (
              <button
                onClick={onEdit}
                className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100"
              >
                <Pencil size={13} />
                Editar
              </button>
            )}
            {event.url && (
              <button
                onClick={() => { navigate(event.url!); onClose() }}
                className="flex items-center gap-1.5 text-xs text-white px-3 py-1.5 rounded-lg ml-auto"
                style={{ backgroundColor: event.color }}
              >
                <ExternalLink size={13} />
                Ver detalle
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
