import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { SiteVisitDocument } from '../types'
import { siteVisitKeys } from './use-site-visits'

export function useUploadDocument(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      file,
      documentType,
      name,
    }: {
      file: File
      documentType: string
      name?: string
    }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      if (name) formData.append('name', name)
      const { data } = await apiClient.post<SiteVisitDocument>(
        `/api/v1/site-visits/${visitId}/documents`,
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

export function useDeleteDocument(visitId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (docId: string) => {
      await apiClient.delete(`/api/v1/site-visits/${visitId}/documents/${docId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(visitId) })
    },
  })
}
