import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  CalendarAggregatedEvent,
  CalendarEventCreate,
  CalendarEventResponse,
  CalendarEventUpdate,
} from '../types'

export const calendarKeys = {
  all: ['calendar'] as const,
  events: (dateFrom: string, dateTo: string) =>
    [...calendarKeys.all, 'events', dateFrom, dateTo] as const,
  customEvents: () => [...calendarKeys.all, 'custom-events'] as const,
}

export function useCalendarEvents(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: calendarKeys.events(dateFrom, dateTo),
    queryFn: async () => {
      const { data } = await apiClient.get<CalendarAggregatedEvent[]>(
        '/api/v1/calendar/events',
        { params: { date_from: dateFrom, date_to: dateTo } }
      )
      return data
    },
    staleTime: 30_000,
  })
}

export function useCustomEvents() {
  return useQuery({
    queryKey: calendarKeys.customEvents(),
    queryFn: async () => {
      const { data } = await apiClient.get<CalendarEventResponse[]>(
        '/api/v1/calendar/custom-events'
      )
      return data
    },
  })
}

export function useCreateCalendarEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: CalendarEventCreate) => {
      const res = await apiClient.post<CalendarEventResponse>(
        '/api/v1/calendar/custom-events',
        data
      )
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: calendarKeys.all })
    },
  })
}

export function useUpdateCalendarEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: CalendarEventUpdate }) => {
      const res = await apiClient.patch<CalendarEventResponse>(
        `/api/v1/calendar/custom-events/${id}`,
        data
      )
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: calendarKeys.all })
    },
  })
}

export function useDeleteCalendarEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/calendar/custom-events/${id}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: calendarKeys.all })
    },
  })
}
