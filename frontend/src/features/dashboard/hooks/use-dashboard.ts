import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { DashboardSummary } from '../types'

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: (dateFrom: string, dateTo: string) =>
    [...dashboardKeys.all, 'summary', dateFrom, dateTo] as const,
}

export function useDashboardSummary(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: dashboardKeys.summary(dateFrom, dateTo),
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardSummary>(
        '/api/v1/dashboard/summary',
        { params: { date_from: dateFrom, date_to: dateTo } },
      )
      return data
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}
