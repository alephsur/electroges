import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { budgetKeys } from './use-budgets'

export function useGeneratePdf(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(
        `/api/v1/budgets/${budgetId}/generate-pdf`,
        null,
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data], { type: 'application/pdf' })
      return URL.createObjectURL(blob)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useDownloadPdf(budgetId: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.get(
        `/api/v1/budgets/${budgetId}/pdf`,
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data], { type: 'application/pdf' })
      return URL.createObjectURL(blob)
    },
  })
}
