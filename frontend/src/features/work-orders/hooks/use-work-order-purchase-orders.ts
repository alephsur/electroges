import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { WorkOrder } from '../types'
import { workOrderKeys } from './use-work-orders'

export interface NewPOLine {
  inventory_item_id?: string | null
  description?: string | null
  quantity: number
  unit_cost: number
}

export interface CreateAndLinkPOPayload {
  workOrderId: string
  supplier_id: string
  order_date: string
  expected_date?: string | null
  notes?: string | null
  lines: NewPOLine[]
}

export function useCreateAndLinkPurchaseOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ workOrderId, ...payload }: CreateAndLinkPOPayload) => {
      const { data } = await apiClient.post<WorkOrder>(
        `/api/v1/work-orders/${workOrderId}/purchase-orders/new`,
        payload,
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: workOrderKeys.detail(vars.workOrderId) })
    },
  })
}

export function useLinkPurchaseOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      purchase_order_id,
      notes,
    }: {
      workOrderId: string
      purchase_order_id: string
      notes?: string
    }) => {
      const { data } = await apiClient.post<WorkOrder>(
        `/api/v1/work-orders/${workOrderId}/purchase-orders`,
        { purchase_order_id, notes },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}

export function useReceivePurchaseOrderFromWorkOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      purchaseOrderId,
    }: {
      workOrderId: string
      purchaseOrderId: string
    }) => {
      const { data } = await apiClient.post<WorkOrder>(
        `/api/v1/work-orders/${workOrderId}/purchase-orders/${purchaseOrderId}/receive`,
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}

export function useUnlinkPurchaseOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      purchaseOrderId,
    }: {
      workOrderId: string
      purchaseOrderId: string
    }) => {
      await apiClient.delete(
        `/api/v1/work-orders/${workOrderId}/purchase-orders/${purchaseOrderId}`,
      )
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}
