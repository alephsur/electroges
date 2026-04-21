import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  WorkOrder,
  WorkOrderFilters,
  WorkOrderListResponse,
} from '../types'

export interface WorkOrderCreatePayload {
  customer_id: string
  address?: string
  notes?: string
}

export const workOrderKeys = {
  all: ['work-orders'] as const,
  lists: () => [...workOrderKeys.all, 'list'] as const,
  list: (filters: WorkOrderFilters) =>
    [...workOrderKeys.lists(), filters] as const,
  detail: (id: string) => [...workOrderKeys.all, id] as const,
  certifiable: (id: string) =>
    [...workOrderKeys.all, id, 'certifiable-tasks'] as const,
}

export function useWorkOrders(filters: WorkOrderFilters) {
  return useQuery({
    queryKey: workOrderKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<WorkOrderListResponse>(
        '/api/v1/work-orders',
        { params: filters },
      )
      return data
    },
  })
}

export function useWorkOrder(id: string | null) {
  return useQuery({
    queryKey: workOrderKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<WorkOrder>(
        `/api/v1/work-orders/${id}`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useUpdateWorkOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: { id: string; address?: string; notes?: string }) => {
      const { data } = await apiClient.patch<WorkOrder>(
        `/api/v1/work-orders/${id}`,
        payload,
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: workOrderKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() })
    },
  })
}

export function useCreateWorkOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: WorkOrderCreatePayload) => {
      const { data } = await apiClient.post<WorkOrder>('/api/v1/work-orders', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() })
    },
  })
}

export function useDeleteWorkOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/work-orders/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() })
    },
  })
}

export function useUpdateWorkOrderStatus() {
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
      const { data } = await apiClient.patch<WorkOrder>(
        `/api/v1/work-orders/${id}/status`,
        { status, notes },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: workOrderKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() })
    },
  })
}
