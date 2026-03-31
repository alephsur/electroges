import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  DeliveryNote,
  DeliveryNoteCreate,
  DeliveryNoteUpdate,
} from '../types'
import { workOrderKeys } from './use-work-orders'

export function useCreateDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      data,
    }: {
      workOrderId: string
      data: DeliveryNoteCreate
    }) => {
      const { data: result } = await apiClient.post<DeliveryNote>(
        `/api/v1/work-orders/${workOrderId}/delivery-notes`,
        data,
      )
      return result
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}

export function useUpdateDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      deliveryNoteId,
      data,
    }: {
      workOrderId: string
      deliveryNoteId: string
      data: DeliveryNoteUpdate
    }) => {
      const { data: result } = await apiClient.patch<DeliveryNote>(
        `/api/v1/work-orders/${workOrderId}/delivery-notes/${deliveryNoteId}`,
        data,
      )
      return result
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}

export function useIssueDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      deliveryNoteId,
    }: {
      workOrderId: string
      deliveryNoteId: string
    }) => {
      const { data } = await apiClient.post<DeliveryNote>(
        `/api/v1/work-orders/${workOrderId}/delivery-notes/${deliveryNoteId}/issue`,
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

export function useDeleteDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      deliveryNoteId,
    }: {
      workOrderId: string
      deliveryNoteId: string
    }) => {
      await apiClient.delete(
        `/api/v1/work-orders/${workOrderId}/delivery-notes/${deliveryNoteId}`,
      )
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}
