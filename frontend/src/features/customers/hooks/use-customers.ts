import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  Customer,
  CustomerAddress,
  CustomerAddressCreatePayload,
  CustomerAddressUpdatePayload,
  CustomerCreatePayload,
  CustomerDocument,
  CustomerFilters,
  CustomerListResponse,
  CustomerTimeline,
  CustomerUpdatePayload,
} from '../types'

export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (filters: CustomerFilters) => [...customerKeys.lists(), filters] as const,
  detail: (id: string) => [...customerKeys.all, id] as const,
  timeline: (id: string) => [...customerKeys.detail(id), 'timeline'] as const,
  addresses: (id: string) => [...customerKeys.detail(id), 'addresses'] as const,
  documents: (id: string) => [...customerKeys.detail(id), 'documents'] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useCustomers(filters: CustomerFilters) {
  return useQuery({
    queryKey: customerKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerListResponse>('/api/v1/customers', {
        params: filters,
      })
      return data
    },
  })
}

export function useCustomer(id: string | null) {
  return useQuery({
    queryKey: customerKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<Customer>(`/api/v1/customers/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCustomerTimeline(id: string | null) {
  return useQuery({
    queryKey: customerKeys.timeline(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerTimeline>(`/api/v1/customers/${id}/timeline`)
      return data
    },
    enabled: !!id,
  })
}

// ── Customer mutations ────────────────────────────────────────────────────────

export function useCreateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CustomerCreatePayload) => {
      const { data } = await apiClient.post<Customer>('/api/v1/customers', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
    },
  })
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }: CustomerUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<Customer>(`/api/v1/customers/${id}`, payload)
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
    },
  })
}

export function useDeactivateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/customers/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.all })
    },
  })
}

// ── Address mutations ─────────────────────────────────────────────────────────

export function useAddAddress(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CustomerAddressCreatePayload) => {
      const { data } = await apiClient.post<CustomerAddress>(
        `/api/v1/customers/${customerId}/addresses`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}

export function useUpdateAddress(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      addressId,
      ...payload
    }: CustomerAddressUpdatePayload & { addressId: string }) => {
      const { data } = await apiClient.patch<CustomerAddress>(
        `/api/v1/customers/${customerId}/addresses/${addressId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}

export function useDeleteAddress(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (addressId: string) => {
      await apiClient.delete(`/api/v1/customers/${customerId}/addresses/${addressId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}

export function useSetDefaultAddress(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (addressId: string) => {
      const { data } = await apiClient.post<CustomerAddress>(
        `/api/v1/customers/${customerId}/addresses/${addressId}/set-default`,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}

// ── Document mutations ────────────────────────────────────────────────────────

export function useUploadDocument(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      file,
      documentType,
      name,
    }: {
      file: File
      documentType: string
      name?: string
    }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      if (name) formData.append('name', name)

      const { data } = await apiClient.post<CustomerDocument>(
        `/api/v1/customers/${customerId}/documents`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}

export function useDeleteDocument(customerId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (documentId: string) => {
      await apiClient.delete(`/api/v1/customers/${customerId}/documents/${documentId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) })
    },
  })
}
