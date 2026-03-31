import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Certification, CertificationItem, Task } from '../types'
import { workOrderKeys } from './use-work-orders'

export function useCertifiableTasks(workOrderId: string | null) {
  return useQuery({
    queryKey: workOrderKeys.certifiable(workOrderId!),
    queryFn: async () => {
      const { data } = await apiClient.get<Task[]>(
        `/api/v1/work-orders/${workOrderId}/certifiable-tasks`,
      )
      return data
    },
    enabled: !!workOrderId,
  })
}

export function useCreateCertification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      items,
      notes,
    }: {
      workOrderId: string
      items: { task_id: string; amount?: number; notes?: string }[]
      notes?: string
    }) => {
      const { data } = await apiClient.post<Certification>(
        `/api/v1/work-orders/${workOrderId}/certifications`,
        { items, notes },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.certifiable(vars.workOrderId),
      })
    },
  })
}

export function useIssueCertification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      certId,
    }: {
      workOrderId: string
      certId: string
    }) => {
      const { data } = await apiClient.post<Certification>(
        `/api/v1/work-orders/${workOrderId}/certifications/${certId}/issue`,
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

export function useDeleteCertification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      workOrderId,
      certId,
    }: {
      workOrderId: string
      certId: string
    }) => {
      await apiClient.delete(
        `/api/v1/work-orders/${workOrderId}/certifications/${certId}`,
      )
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: workOrderKeys.detail(vars.workOrderId),
      })
    },
  })
}
