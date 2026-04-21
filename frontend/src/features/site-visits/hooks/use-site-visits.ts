import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  SiteVisit,
  SiteVisitCreatePayload,
  SiteVisitFilters,
  SiteVisitListResponse,
  SiteVisitUpdatePayload,
} from '../types'

export const siteVisitKeys = {
  all: ['site-visits'] as const,
  lists: () => [...siteVisitKeys.all, 'list'] as const,
  list: (filters: SiteVisitFilters) => [...siteVisitKeys.lists(), filters] as const,
  detail: (id: string) => [...siteVisitKeys.all, id] as const,
}

export function useSiteVisits(filters: SiteVisitFilters) {
  return useQuery({
    queryKey: siteVisitKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<SiteVisitListResponse>('/api/v1/site-visits', {
        params: filters,
      })
      return data
    },
  })
}

export function useSiteVisit(id: string | null) {
  return useQuery({
    queryKey: siteVisitKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<SiteVisit>(`/api/v1/site-visits/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateSiteVisit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SiteVisitCreatePayload) => {
      const { data } = await apiClient.post<SiteVisit>('/api/v1/site-visits', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() })
    },
  })
}

export function useUpdateSiteVisit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }: SiteVisitUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<SiteVisit>(`/api/v1/site-visits/${id}`, payload)
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() })
    },
  })
}

export function useUpdateSiteVisitStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      status,
      notes,
    }: {
      id: string
      status: string
      notes?: string
    }) => {
      const { data } = await apiClient.patch<SiteVisit>(
        `/api/v1/site-visits/${id}/status`,
        { status, notes },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() })
    },
  })
}

export function useDeleteSiteVisit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/site-visits/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() })
    },
  })
}

export function useLinkCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      visitId,
      customerId,
      customerAddressId,
    }: {
      visitId: string
      customerId: string
      customerAddressId?: string
    }) => {
      const { data } = await apiClient.post<SiteVisit>(
        `/api/v1/site-visits/${visitId}/link-customer`,
        { customer_id: customerId, customer_address_id: customerAddressId ?? null },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(vars.visitId) })
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() })
    },
  })
}
