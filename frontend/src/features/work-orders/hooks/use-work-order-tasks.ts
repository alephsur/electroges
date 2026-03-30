import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Task, TaskStatus, WorkOrder } from '../types'
import { workOrderKeys } from './use-work-orders'

export function useAddTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      ...payload
    }: {
      workOrderId: string
      name: string
      description?: string
      unit_price?: number
      estimated_hours?: number
      sort_order?: number
    }) => {
      const { data } = await apiClient.post<Task>(
        `/api/v1/work-orders/${workOrderId}/tasks`,
        payload,
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

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      taskId,
      ...payload
    }: {
      workOrderId: string
      taskId: string
      name?: string
      description?: string
      unit_price?: number | null
      estimated_hours?: number
      actual_hours?: number
    }) => {
      const { data } = await apiClient.patch<Task>(
        `/api/v1/work-orders/${workOrderId}/tasks/${taskId}`,
        payload,
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

export function useUpdateTaskStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      taskId,
      status,
      actual_hours,
    }: {
      workOrderId: string
      taskId: string
      status: TaskStatus
      actual_hours?: number
    }) => {
      const { data } = await apiClient.patch<WorkOrder>(
        `/api/v1/work-orders/${workOrderId}/tasks/${taskId}/status`,
        { status, actual_hours },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
      queryClient.invalidateQueries({ queryKey: workOrderKeys.lists() })
    },
  })
}

export function useDeleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      taskId,
    }: {
      workOrderId: string
      taskId: string
    }) => {
      await apiClient.delete(
        `/api/v1/work-orders/${workOrderId}/tasks/${taskId}`,
      )
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}

export function useAddMaterial() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      ...payload
    }: {
      workOrderId: string
      inventory_item_id: string
      task_id: string
      estimated_quantity: number
      unit_cost?: number
    }) => {
      const { data } = await apiClient.post<Task>(
        `/api/v1/work-orders/${workOrderId}/materials`,
        payload,
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

export function useRemoveMaterial() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      taskId,
      materialId,
    }: {
      workOrderId: string
      taskId: string
      materialId: string
    }) => {
      const { data } = await apiClient.delete<Task>(
        `/api/v1/work-orders/${workOrderId}/tasks/${taskId}/materials/${materialId}`,
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

export function useConsumeMaterial() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      taskId,
      materialId,
      consumed_quantity,
      notes,
    }: {
      workOrderId: string
      taskId: string
      materialId: string
      consumed_quantity: number
      notes?: string
    }) => {
      const { data } = await apiClient.post<Task>(
        `/api/v1/work-orders/${workOrderId}/tasks/${taskId}/materials/${materialId}/consume`,
        { consumed_quantity, notes },
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
