export type CalendarEventType = 'site_visit' | 'budget' | 'work_order' | 'custom'

export interface CalendarAggregatedEvent {
  id: string
  title: string
  description: string | null
  start: string // ISO 8601 date or datetime
  end: string | null
  all_day: boolean
  color: string
  event_type: CalendarEventType
  entity_id: string | null
  url: string | null
}

export interface CalendarEventCreate {
  title: string
  description?: string | null
  start_datetime: string
  end_datetime?: string | null
  all_day: boolean
  color: string
}

export interface CalendarEventUpdate {
  title?: string
  description?: string | null
  start_datetime?: string
  end_datetime?: string | null
  all_day?: boolean
  color?: string
}

export interface CalendarEventResponse {
  id: string
  title: string
  description: string | null
  start_datetime: string
  end_datetime: string | null
  all_day: boolean
  color: string
  created_by: string | null
}
