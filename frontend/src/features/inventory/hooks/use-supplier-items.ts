import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { SupplierItem, SupplierItemCreatePayload, SupplierItemUpdatePayload } from '../types'
import { inventoryKeys } from './use-inventory-items'

export function useAddSupplierToItem(itemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SupplierItemCreatePayload) => {
      const { data } = await apiClient.post<SupplierItem>(
        `/api/v1/inventory/${itemId}/suppliers`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(itemId) })
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
    },
  })
}

export function useUpdateSupplierPrice(itemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      supplierItemId,
      ...payload
    }: SupplierItemUpdatePayload & { supplierItemId: string }) => {
      const { data } = await apiClient.patch<SupplierItem>(
        `/api/v1/inventory/${itemId}/suppliers/${supplierItemId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(itemId) })
    },
  })
}

export function useRemoveSupplier(itemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (supplierItemId: string) => {
      await apiClient.delete(`/api/v1/inventory/${itemId}/suppliers/${supplierItemId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(itemId) })
    },
  })
}

export function useSetPreferredSupplier(itemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (supplierItemId: string) => {
      const { data } = await apiClient.post<SupplierItem>(
        `/api/v1/inventory/${itemId}/suppliers/${supplierItemId}/set-preferred`,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.detail(itemId) })
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
    },
  })
}
