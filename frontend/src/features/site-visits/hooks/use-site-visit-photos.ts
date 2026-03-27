import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { SiteVisitPhoto } from '../types'
import { siteVisitKeys } from './use-site-visits'

export function useUploadPhoto(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, caption }: { file: File; caption?: string }) => {
      const formData = new FormData()
      formData.append('file', file)
      if (caption) formData.append('caption', caption)
      const { data } = await apiClient.post<SiteVisitPhoto>(
        `/api/v1/site-visits/${visitId}/photos`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}

export function useUpdatePhoto(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      photoId,
      caption,
      sortOrder,
    }: {
      photoId: string
      caption?: string | null
      sortOrder?: number
    }) => {
      const { data } = await apiClient.patch<SiteVisitPhoto>(
        `/api/v1/site-visits/${visitId}/photos/${photoId}`,
        { caption, sort_order: sortOrder },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}

export function useDeletePhoto(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (photoId: string) => {
      await apiClient.delete(`/api/v1/site-visits/${visitId}/photos/${photoId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}

export function useReorderPhotos(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (photoIds: string[]) => {
      const { data } = await apiClient.put<SiteVisitPhoto[]>(
        `/api/v1/site-visits/${visitId}/photos/reorder`,
        { photo_ids: photoIds },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}
