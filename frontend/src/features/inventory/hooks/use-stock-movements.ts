import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { StockMovement } from '../types'
import { inventoryKeys } from './use-inventory-items'

export function useItemMovements(itemId: string | null, skip = 0, limit = 20) {
  return useQuery({
    queryKey: inventoryKeys.movements(itemId!, skip),
    queryFn: async () => {
      const { data } = await apiClient.get<StockMovement[]>(
        `/api/v1/inventory/${itemId}/movements`,
        { params: { skip, limit } },
      )
      return data
    },
    enabled: !!itemId,
  })
}
