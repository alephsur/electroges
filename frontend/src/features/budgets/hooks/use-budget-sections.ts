import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  BudgetSection,
  BudgetSectionCreatePayload,
  BudgetSectionUpdatePayload,
} from '../types'
import { budgetKeys } from './use-budgets'

export function useCreateSection(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BudgetSectionCreatePayload) => {
      const { data } = await apiClient.post<BudgetSection>(
        `/api/v1/budgets/${budgetId}/sections`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useUpdateSection(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      sectionId,
      ...payload
    }: BudgetSectionUpdatePayload & { sectionId: string }) => {
      const { data } = await apiClient.patch<BudgetSection>(
        `/api/v1/budgets/${budgetId}/sections/${sectionId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useDeleteSection(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sectionId: string) => {
      await apiClient.delete(
        `/api/v1/budgets/${budgetId}/sections/${sectionId}`,
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useReorderSections(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sectionIds: string[]) => {
      const { data } = await apiClient.put(
        `/api/v1/budgets/${budgetId}/sections/reorder`,
        { section_ids: sectionIds },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useAssignLineToSection(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      lineId,
      sectionId,
    }: {
      lineId: string
      sectionId: string | null
    }) => {
      const { data } = await apiClient.patch(
        `/api/v1/budgets/${budgetId}/lines/${lineId}/section`,
        { section_id: sectionId },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}
