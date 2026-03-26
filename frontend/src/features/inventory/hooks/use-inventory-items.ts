import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  InventoryFilters,
  InventoryItem,
  InventoryItemCreatePayload,
  InventoryItemListResponse,
  InventoryItemUpdatePayload,
  ManualAdjustmentPayload,
} from '../types'

export const inventoryKeys = {
  all: ['inventory'] as const,
  lists: () => [...inventoryKeys.all, 'list'] as const,
  list: (filters: InventoryFilters) => [...inventoryKeys.lists(), filters] as const,
  detail: (id: string) => [...inventoryKeys.all, id] as const,
  alerts: () => [...inventoryKeys.all, 'alerts'] as const,
  movements: (id: string, skip: number) =>
    [...inventoryKeys.detail(id), 'movements', skip] as const,
}

export function useInventoryItems(filters: InventoryFilters) {
  return useQuery({
    queryKey: inventoryKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<InventoryItemListResponse>('/api/v1/inventory', {
        params: filters,
      })
      return data
    },
  })
}

export function useInventoryItem(id: string | null) {
  return useQuery({
    queryKey: inventoryKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<InventoryItem>(`/api/v1/inventory/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useLowStockAlerts() {
  return useQuery({
    queryKey: inventoryKeys.alerts(),
    queryFn: async () => {
      const { data } = await apiClient.get<InventoryItem[]>('/api/v1/inventory/alerts')
      return data
    },
  })
}

export function useCreateInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InventoryItemCreatePayload) => {
      const { data } = await apiClient.post<InventoryItem>('/api/v1/inventory', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all })
    },
  })
}

export function useUpdateInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }: InventoryItemUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<InventoryItem>(`/api/v1/inventory/${id}`, payload)
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
    },
  })
}

export function useDeactivateInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.delete<InventoryItem>(`/api/v1/inventory/${id}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all })
    },
  })
}

export function useManualAdjustment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ itemId, ...payload }: ManualAdjustmentPayload & { itemId: string }) => {
      const { data } = await apiClient.post<InventoryItem>(
        `/api/v1/inventory/${itemId}/adjust`,
        payload,
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(vars.itemId) })
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: inventoryKeys.alerts() })
    },
  })
}
