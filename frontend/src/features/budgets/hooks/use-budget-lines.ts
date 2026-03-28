import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { BudgetLine, BudgetLineCreatePayload, BudgetLineUpdatePayload } from '../types'
import { budgetKeys } from './use-budgets'

export function useAddLine(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BudgetLineCreatePayload) => {
      const { data } = await apiClient.post<BudgetLine>(
        `/api/v1/budgets/${budgetId}/lines`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useUpdateLine(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      lineId,
      ...payload
    }: BudgetLineUpdatePayload & { lineId: string }) => {
      const { data } = await apiClient.patch<BudgetLine>(
        `/api/v1/budgets/${budgetId}/lines/${lineId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useDeleteLine(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (lineId: string) => {
      await apiClient.delete(`/api/v1/budgets/${budgetId}/lines/${lineId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useReorderLines(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (lineIds: string[]) => {
      const { data } = await apiClient.put(
        `/api/v1/budgets/${budgetId}/lines/reorder`,
        { line_ids: lineIds },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}
