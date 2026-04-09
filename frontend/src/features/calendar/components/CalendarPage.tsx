import { useState } from 'react'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCalendarStore } from '../store/calendar-store'
import { useCalendarEvents } from '../hooks/use-calendar'
import { CalendarGrid } from './CalendarGrid'
import { CalendarLegend } from './CalendarLegend'
import { EventFormModal } from './EventFormModal'
import { EventDetailPopover } from './EventDetailPopover'
import type { CalendarAggregatedEvent, CalendarEventResponse } from '../types'

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

export function CalendarPage() {
  const { currentDate, view, setView, goToPrev, goToNext, goToToday } = useCalendarStore()
  const [showForm, setShowForm] = useState(false)
  const [formDate, setFormDate] = useState<string | null>(null)
  const [editEvent, setEditEvent] = useState<CalendarEventResponse | null>(null)
  const [detailEvent, setDetailEvent] = useState<CalendarAggregatedEvent | null>(null)

  // Compute range for the current view
  const rangeStart = view === 'month'
    ? currentDate.startOf('month').subtract(6, 'day').format('YYYY-MM-DD')
    : currentDate.startOf('week').subtract(1, 'day').format('YYYY-MM-DD')

  const rangeEnd = view === 'month'
    ? currentDate.endOf('month').add(6, 'day').format('YYYY-MM-DD')
    : currentDate.endOf('week').add(1, 'day').format('YYYY-MM-DD')

  const { data: events = [], isLoading } = useCalendarEvents(rangeStart, rangeEnd)

  const title = view === 'month'
    ? `${MONTH_NAMES[currentDate.month()]} ${currentDate.year()}`
    : `Semana del ${currentDate.startOf('week').add(1, 'day').format('D MMM')} – ${currentDate.endOf('week').add(1, 'day').format('D MMM YYYY')}`

  const handleDayClick = (dateStr: string) => {
    setFormDate(dateStr)
    setEditEvent(null)
    setShowForm(true)
  }

  const handleEventClick = (ev: CalendarAggregatedEvent) => {
    setDetailEvent(ev)
  }

  const handleEditFromDetail = () => {
    if (!detailEvent || detailEvent.event_type !== 'custom' || !detailEvent.entity_id) return
    // Build a minimal CalendarEventResponse to prefill the form
    setEditEvent({
      id: detailEvent.entity_id,
      title: detailEvent.title,
      description: detailEvent.description,
      start_datetime: detailEvent.start,
      end_datetime: detailEvent.end,
      all_day: detailEvent.all_day,
      color: detailEvent.color,
      created_by: null,
    })
    setDetailEvent(null)
    setShowForm(true)
  }

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Navigation */}
          <button
            onClick={goToPrev}
            className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-100 text-gray-600"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={goToNext}
            className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-100 text-gray-600"
          >
            <ChevronRight size={16} />
          </button>
          <h1 className="text-lg font-semibold text-gray-900 capitalize">{title}</h1>
          <button
            onClick={goToToday}
            className="px-3 py-1 text-xs font-medium text-brand-700 bg-brand-50 rounded-full hover:bg-brand-100"
          >
            Hoy
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* View switcher */}
          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
            <button
              onClick={() => setView('month')}
              className={[
                'px-3 py-1.5 font-medium transition-colors',
                view === 'month' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-50',
              ].join(' ')}
            >
              Mes
            </button>
            <button
              onClick={() => setView('week')}
              className={[
                'px-3 py-1.5 font-medium transition-colors border-l border-gray-200',
                view === 'week' ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-50',
              ].join(' ')}
            >
              Semana
            </button>
          </div>

          {/* New event */}
          <button
            onClick={() => { setFormDate(null); setEditEvent(null); setShowForm(true) }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700"
          >
            <Plus size={15} />
            Nuevo evento
          </button>
        </div>
      </div>

      {/* Legend */}
      <CalendarLegend />

      {/* Loading skeleton */}
      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
          Cargando eventos...
        </div>
      )}

      {/* Grid */}
      {!isLoading && (
        <CalendarGrid
          view={view}
          currentDate={currentDate}
          events={events}
          onDayClick={handleDayClick}
          onEventClick={handleEventClick}
        />
      )}

      {/* Event form modal */}
      {showForm && (
        <EventFormModal
          onClose={() => setShowForm(false)}
          initialDate={formDate}
          editEvent={editEvent}
        />
      )}

      {/* Event detail popover */}
      {detailEvent && (
        <EventDetailPopover
          event={detailEvent}
          onClose={() => setDetailEvent(null)}
          onEdit={handleEditFromDetail}
        />
      )}
    </div>
  )
}
