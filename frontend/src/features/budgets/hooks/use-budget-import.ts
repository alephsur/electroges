import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { ImportLineRow, ImportPreview } from '../types'
import { budgetKeys } from './use-budgets'

export function usePreviewImport(budgetId: string) {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await apiClient.post<ImportPreview>(
        `/api/v1/budgets/${budgetId}/import-lines/preview`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return data
    },
  })
}

export function useConfirmImport(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (rows: ImportLineRow[]) => {
      const { data } = await apiClient.post(
        `/api/v1/budgets/${budgetId}/import-lines/confirm`,
        { rows },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}
