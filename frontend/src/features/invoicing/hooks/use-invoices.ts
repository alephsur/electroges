import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  Invoice,
  InvoiceCreatePayload,
  InvoiceFilters,
  InvoiceFromWorkOrderPayload,
  InvoiceListResponse,
  InvoiceUpdatePayload,
  RectificationPayload,
} from '../types'

export const invoiceKeys = {
  all: ['invoices'] as const,
  lists: () => [...invoiceKeys.all, 'list'] as const,
  list: (filters: InvoiceFilters) =>
    [...invoiceKeys.lists(), filters] as const,
  detail: (id: string) => [...invoiceKeys.all, id] as const,
  overdue: () => [...invoiceKeys.all, 'overdue'] as const,
}

export function useInvoices(filters: InvoiceFilters) {
  return useQuery({
    queryKey: invoiceKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<InvoiceListResponse>(
        '/api/v1/invoices',
        { params: filters },
      )
      return data
    },
  })
}

export function useInvoice(id: string | null) {
  return useQuery({
    queryKey: invoiceKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<Invoice>(
        `/api/v1/invoices/${id}`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useOverdueInvoices() {
  return useQuery({
    queryKey: invoiceKeys.overdue(),
    queryFn: async () => {
      const { data } = await apiClient.get<InvoiceListResponse>(
        '/api/v1/invoices',
        { params: { overdue_only: true, limit: 10 } },
      )
      return data
    },
  })
}

export function useCreateInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InvoiceCreatePayload) => {
      const { data } = await apiClient.post<Invoice>(
        '/api/v1/invoices',
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useCreateInvoiceFromWorkOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InvoiceFromWorkOrderPayload) => {
      const { data } = await apiClient.post<Invoice>(
        '/api/v1/invoices/from-work-order',
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useUpdateInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: { id: string } & InvoiceUpdatePayload) => {
      const { data } = await apiClient.patch<Invoice>(
        `/api/v1/invoices/${id}`,
        payload,
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(vars.id),
      })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useSendInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<Invoice>(
        `/api/v1/invoices/${id}/send`,
      )
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/invoices/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useCancelInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      const { data } = await apiClient.post<Invoice>(
        `/api/v1/invoices/${id}/cancel`,
        null,
        { params: { reason } },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: invoiceKeys.detail(vars.id),
      })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

export function useCreateRectification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: { id: string } & RectificationPayload) => {
      const { data } = await apiClient.post<Invoice>(
        `/api/v1/invoices/${id}/rectify`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}
