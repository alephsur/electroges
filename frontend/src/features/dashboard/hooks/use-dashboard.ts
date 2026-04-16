import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { DashboardSummary, RecentActivityPage } from '../types'

export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: (dateFrom: string, dateTo: string) =>
    [...dashboardKeys.all, 'summary', dateFrom, dateTo] as const,
  activity: (page: number, pageSize: number) =>
    [...dashboardKeys.all, 'activity', page, pageSize] as const,
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

export function useRecentActivity(page: number, pageSize: number = 10) {
  return useQuery({
    queryKey: dashboardKeys.activity(page, pageSize),
    queryFn: async () => {
      const { data } = await apiClient.get<RecentActivityPage>(
        '/api/v1/dashboard/activity',
        { params: { page, page_size: pageSize } },
      )
      return data
    },
    staleTime: 60 * 1000, // 1 minute
    placeholderData: (prev) => prev,
  })
}
