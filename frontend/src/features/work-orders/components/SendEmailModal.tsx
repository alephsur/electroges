import { useState } from 'react'
import { X } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useSendDocumentEmail } from '../hooks/use-document-actions'

interface SendEmailModalProps {
  apiUrl: string
  defaultEmail?: string
  documentLabel: string  // e.g. "albarán ALBAR-OBRA-2026-0001-01"
  onClose: () => void
}

export function SendEmailModal({
  apiUrl,
  defaultEmail,
  documentLabel,
  onClose,
}: SendEmailModalProps) {
  const [toEmail, setToEmail] = useState(defaultEmail ?? '')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState(false)
  const send = useSendDocumentEmail(apiUrl)

  const handleSend = async () => {
    if (!toEmail) return
    try {
      await send.mutateAsync({
        to_email: toEmail,
        subject: subject || undefined,
        message: message || undefined,
      })
      setSent(true)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            Enviar por email
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100"
          >
            <X size={16} />
          </button>
        </div>

        {sent ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-green-50 p-4 text-sm text-green-700">
              Email enviado correctamente a <strong>{toEmail}</strong>.
            </div>
            <button
              onClick={onClose}
              className="w-full rounded-md bg-gray-100 py-2 text-sm text-gray-700 hover:bg-gray-200"
            >
              Cerrar
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">
              Se adjuntará el PDF del {documentLabel}.
            </p>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Destinatario *
              </label>
              <input
                type="email"
                value={toEmail}
                onChange={(e) => setToEmail(e.target.value)}
                placeholder="cliente@ejemplo.com"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Asunto (opcional)
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Se usará el asunto por defecto"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Mensaje personalizado (opcional)
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Si se deja vacío se usará el mensaje por defecto"
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex gap-2 pt-1">
              <button
                onClick={handleSend}
                disabled={!toEmail || send.isPending}
                className="flex-1 rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {send.isPending ? 'Enviando…' : 'Enviar email'}
              </button>
              <button
                onClick={onClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
