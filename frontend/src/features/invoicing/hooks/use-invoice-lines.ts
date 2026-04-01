import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Invoice, InvoiceLineCreatePayload } from '../types'
import { invoiceKeys } from './use-invoices'

export function useAddInvoiceLine(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InvoiceLineCreatePayload) => {
      const { data } = await apiClient.post<Invoice>(
        `/api/v1/invoices/${invoiceId}/lines`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
    },
  })
}

export function useUpdateInvoiceLine(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      lineId,
      ...payload
    }: {
      lineId: string
      description?: string
      quantity?: number
      unit?: string | null
      unit_price?: number
      line_discount_pct?: number
      sort_order?: number
    }) => {
      const { data } = await apiClient.patch<Invoice>(
        `/api/v1/invoices/${invoiceId}/lines/${lineId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
    },
  })
}

export function useDeleteInvoiceLine(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (lineId: string) => {
      const { data } = await apiClient.delete<Invoice>(
        `/api/v1/invoices/${invoiceId}/lines/${lineId}`,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
    },
  })
}

export function useReorderInvoiceLines(invoiceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (lineIds: string[]) => {
      const { data } = await apiClient.put<Invoice>(
        `/api/v1/invoices/${invoiceId}/lines/reorder`,
        { line_ids: lineIds },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(invoiceId),
      })
    },
  })
}
