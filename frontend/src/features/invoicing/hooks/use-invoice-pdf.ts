import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { PaymentReminderResponse } from '../types'
import { invoiceKeys } from './use-invoices'

export function useGenerateInvoicePdf(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(
        `/api/v1/invoices/${invoiceId}/generate-pdf`,
        null,
        { responseType: 'blob' },
      )
      const url = URL.createObjectURL(response.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `factura_${invoiceId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
    },
  })
}

export function useDownloadInvoicePdf(invoiceId: string, invoiceNumber: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.get(
        `/api/v1/invoices/${invoiceId}/pdf`,
        { responseType: 'blob' },
      )
      const url = URL.createObjectURL(response.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `factura_${invoiceNumber}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}

export function usePaymentReminder(invoiceId: string) {
  return useQuery({
    queryKey: [...invoiceKeys.detail(invoiceId), 'reminder'],
    queryFn: async () => {
      const { data } = await apiClient.get<PaymentReminderResponse>(
        `/api/v1/invoices/${invoiceId}/reminder`,
      )
      return data
    },
    enabled: false,
  })
}
