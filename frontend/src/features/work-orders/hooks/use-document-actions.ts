/**
 * Shared hooks for PDF download, email and WhatsApp actions
 * used by both delivery notes and certifications.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface WhatsAppLinkResponse {
  url: string
  phone: string
}

// ── PDF download ──────────────────────────────────────────────────────────────

export function useDownloadPdf() {
  const [isDownloading, setIsDownloading] = useState(false)

  const download = async (url: string, filename: string) => {
    setIsDownloading(true)
    try {
      const response = await apiClient.get<Blob>(url, { responseType: 'blob' })
      const blob = new Blob([response.data as unknown as BlobPart], {
        type: 'application/pdf',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = filename
      link.click()
      URL.revokeObjectURL(link.href)
    } finally {
      setIsDownloading(false)
    }
  }

  return { download, isDownloading }
}

// ── Email send ────────────────────────────────────────────────────────────────

export function useSendDocumentEmail(url: string) {
  return useMutation({
    mutationFn: async ({
      to_email,
      subject,
      message,
    }: {
      to_email: string
      subject?: string
      message?: string
    }) => {
      await apiClient.post(url, { to_email, subject, message })
    },
  })
}

// ── WhatsApp link ─────────────────────────────────────────────────────────────

export function useOpenWhatsApp() {
  const [isLoading, setIsLoading] = useState(false)

  const open = async (url: string, phone?: string) => {
    setIsLoading(true)
    try {
      const params = phone ? `?phone=${encodeURIComponent(phone)}` : ''
      const { data } = await apiClient.get<WhatsAppLinkResponse>(`${url}${params}`)
      window.open(data.url, '_blank', 'noopener,noreferrer')
    } finally {
      setIsLoading(false)
    }
  }

  return { open, isLoading }
}
