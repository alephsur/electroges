import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  SiteVisitMaterial,
  SiteVisitMaterialCreatePayload,
  SiteVisitMaterialUpdatePayload,
} from '../types'
import { siteVisitKeys } from './use-site-visits'

export function useAddMaterial(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SiteVisitMaterialCreatePayload) => {
      const { data } = await apiClient.post<SiteVisitMaterial>(
        `/api/v1/site-visits/${visitId}/materials`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}

export function useUpdateMaterial(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      materialId,
      ...payload
    }: SiteVisitMaterialUpdatePayload & { materialId: string }) => {
      const { data } = await apiClient.patch<SiteVisitMaterial>(
        `/api/v1/site-visits/${visitId}/materials/${materialId}`,
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}

export function useDeleteMaterial(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (materialId: string) => {
      await apiClient.delete(`/api/v1/site-visits/${visitId}/materials/${materialId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}
