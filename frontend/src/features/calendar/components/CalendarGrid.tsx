/**
 * CalendarGrid — custom month/week calendar built with dayjs + Tailwind.
 * No external calendar library needed.
 */
import { useMemo, useState } from 'react'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'
import type { CalendarAggregatedEvent } from '../types'

const DAY_NAMES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

const EVENT_TYPE_LABELS: Record<string, string> = {
  site_visit: 'Visita',
  budget: 'Presupuesto',
  work_order: 'Obra',
  custom: 'Evento',
}

interface DayCell {
  date: dayjs.Dayjs
  isCurrentMonth: boolean
  isToday: boolean
}

interface EventInCell {
  event: CalendarAggregatedEvent
  /** how many days this event spans starting from this cell's date */
  spanDays: number
  /** true if this is not the first cell of a multi-day event in this row */
  isContinuation: boolean
}

function buildMonthGrid(current: dayjs.Dayjs): DayCell[][] {
  const startOfMonth = current.startOf('month')
  // Week starts on Monday (dayjs: 1=Mon, 7=Sun)
  let startDay = startOfMonth.day() // 0=Sun ... 6=Sat
  startDay = startDay === 0 ? 6 : startDay - 1 // shift so 0=Mon
  const firstCell = startOfMonth.subtract(startDay, 'day')
  const today = dayjs().startOf('day')

  const weeks: DayCell[][] = []
  let day = firstCell
  for (let w = 0; w < 6; w++) {
    const week: DayCell[] = []
    for (let d = 0; d < 7; d++) {
      week.push({
        date: day,
        isCurrentMonth: day.month() === current.month(),
        isToday: day.isSame(today, 'day'),
      })
      day = day.add(1, 'day')
    }
    // Skip last row if it belongs entirely to next month
    if (w === 5 && week.every((c) => !c.isCurrentMonth)) break
    weeks.push(week)
  }
  return weeks
}

function buildWeekGrid(current: dayjs.Dayjs): DayCell[] {
  let startDay = current.day()
  startDay = startDay === 0 ? 6 : startDay - 1
  const monday = current.subtract(startDay, 'day')
  const today = dayjs().startOf('day')
  return Array.from({ length: 7 }, (_, i) => {
    const d = monday.add(i, 'day')
    return { date: d, isCurrentMonth: true, isToday: d.isSame(today, 'day') }
  })
}

function getEventsForDay(
  date: dayjs.Dayjs,
  events: CalendarAggregatedEvent[],
  rowStart: dayjs.Dayjs,
  rowEnd: dayjs.Dayjs
): EventInCell[] {
  const dateStr = date.format('YYYY-MM-DD')
  const result: EventInCell[] = []

  for (const ev of events) {
    const evStart = ev.start.slice(0, 10)
    const evEnd = ev.end ? ev.end.slice(0, 10) : evStart

    if (dateStr < evStart || dateStr > evEnd) continue

    const isContinuation = dateStr > evStart && dateStr > rowStart.format('YYYY-MM-DD')
    // How many days does it span from this cell within this row?
    const spanEnd = evEnd < rowEnd.format('YYYY-MM-DD') ? evEnd : rowEnd.format('YYYY-MM-DD')
    const spanDays = dayjs(spanEnd).diff(dayjs(dateStr), 'day') + 1

    result.push({ event: ev, spanDays, isContinuation })
  }

  // Sort: multi-day first, then by start
  result.sort((a, b) => {
    const aSpan = a.spanDays
    const bSpan = b.spanDays
    if (aSpan !== bSpan) return bSpan - aSpan
    return a.event.start.localeCompare(b.event.start)
  })

  return result
}

interface EventPillProps {
  item: EventInCell
  onClick: (e: React.MouseEvent, ev: CalendarAggregatedEvent) => void
}

function EventPill({ item, onClick }: EventPillProps) {
  const { event, spanDays, isContinuation } = item
  const typeLabel = EVENT_TYPE_LABELS[event.event_type] ?? ''

  return (
    <button
      onClick={(e) => onClick(e, event)}
      title={`${event.title}${event.description ? '\n' + event.description : ''}`}
      className="block text-left w-full text-xs rounded px-1.5 py-0.5 truncate font-medium text-white transition-opacity hover:opacity-90 focus:outline-none"
      style={{
        backgroundColor: event.color,
        marginLeft: isContinuation ? 0 : undefined,
        // For multi-day, we rely on cell width + truncate
      }}
    >
      {!isContinuation && (
        <span className="opacity-80 mr-1">[{typeLabel}]</span>
      )}
      {event.title}
    </button>
  )
}

interface Props {
  view: 'month' | 'week'
  currentDate: dayjs.Dayjs
  events: CalendarAggregatedEvent[]
  onDayClick: (dateStr: string) => void
  onEventClick: (ev: CalendarAggregatedEvent) => void
}

export function CalendarGrid({ view, currentDate, events, onDayClick, onEventClick }: Props) {
  const navigate = useNavigate()

  const handleEventClick = (e: React.MouseEvent, ev: CalendarAggregatedEvent) => {
    e.stopPropagation()
    if (ev.event_type === 'custom') {
      onEventClick(ev)
    } else if (ev.url) {
      navigate(ev.url)
    }
  }

  if (view === 'month') {
    const weeks = buildMonthGrid(currentDate)

    return (
      <div className="flex-1 flex flex-col border border-gray-200 rounded-xl overflow-hidden bg-white">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-gray-200">
          {DAY_NAMES.map((d) => (
            <div key={d} className="py-2 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {d}
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="flex-1 grid" style={{ gridTemplateRows: `repeat(${weeks.length}, 1fr)` }}>
          {weeks.map((week, wi) => {
            const rowStart = week[0].date
            const rowEnd = week[6].date
            return (
              <div key={wi} className="grid grid-cols-7 border-b border-gray-100 last:border-b-0">
                {week.map((cell, di) => {
                  const cellEvents = getEventsForDay(cell.date, events, rowStart, rowEnd)
                  const dateStr = cell.date.format('YYYY-MM-DD')
                  return (
                    <div
                      key={di}
                      onClick={() => onDayClick(dateStr)}
                      className={[
                        'border-r border-gray-100 last:border-r-0 p-1 min-h-[80px] cursor-pointer',
                        'hover:bg-gray-50 transition-colors',
                        !cell.isCurrentMonth ? 'bg-gray-50/60' : '',
                      ].join(' ')}
                    >
                      {/* Day number */}
                      <div className="flex justify-end mb-1">
                        <span
                          className={[
                            'text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full',
                            cell.isToday
                              ? 'bg-brand-600 text-white'
                              : cell.isCurrentMonth
                              ? 'text-gray-800'
                              : 'text-gray-400',
                          ].join(' ')}
                        >
                          {cell.date.date()}
                        </span>
                      </div>

                      {/* Events (max 3 visible) */}
                      <div className="space-y-0.5">
                        {cellEvents.slice(0, 3).map((item) => (
                          <EventPill
                            key={item.event.id + dateStr}
                            item={item}
                            onClick={handleEventClick}
                          />
                        ))}
                        {cellEvents.length > 3 && (
                          <p className="text-xs text-gray-500 pl-1">+{cellEvents.length - 3} más</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Week view
  const days = buildWeekGrid(currentDate)
  return (
    <div className="flex-1 flex flex-col border border-gray-200 rounded-xl overflow-hidden bg-white">
      <div className="grid grid-cols-7 border-b border-gray-200">
        {days.map((cell, i) => (
          <div key={i} className="py-3 text-center border-r border-gray-100 last:border-r-0">
            <p className="text-xs font-semibold text-gray-500 uppercase">{DAY_NAMES[i]}</p>
            <span
              className={[
                'mt-1 text-sm font-medium w-8 h-8 flex items-center justify-center rounded-full mx-auto',
                cell.isToday ? 'bg-brand-600 text-white' : 'text-gray-800',
              ].join(' ')}
            >
              {cell.date.date()}
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 flex-1">
        {days.map((cell, di) => {
          const rowStart = days[0].date
          const rowEnd = days[6].date
          const cellEvents = getEventsForDay(cell.date, events, rowStart, rowEnd)
          const dateStr = cell.date.format('YYYY-MM-DD')
          return (
            <div
              key={di}
              onClick={() => onDayClick(dateStr)}
              className="border-r border-gray-100 last:border-r-0 p-2 cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <div className="space-y-1">
                {cellEvents.map((item) => (
                  <EventPill
                    key={item.event.id + dateStr}
                    item={item}
                    onClick={handleEventClick}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
