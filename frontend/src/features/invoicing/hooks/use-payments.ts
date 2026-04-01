import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Invoice, PaymentCreatePayload } from '../types'
import { invoiceKeys } from './use-invoices'

export function useRegisterPayment(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: PaymentCreatePayload) => {
      const { data } = await apiClient.post<Invoice>(
        `/api/v1/invoices/${invoiceId}/payments`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useDeletePayment(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (paymentId: string) => {
      const { data } = await apiClient.delete<Invoice>(
        `/api/v1/invoices/${invoiceId}/payments/${paymentId}`,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}
