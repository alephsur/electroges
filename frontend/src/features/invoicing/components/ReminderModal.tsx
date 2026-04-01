import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import type { PaymentReminderResponse } from '../types'

interface Props {
  reminder: PaymentReminderResponse
  onClose: () => void
}

export function ReminderModal({ reminder, onClose }: Props) {
  const [text, setText] = useState(reminder.reminder_text)
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">
              Recordatorio de cobro
            </h2>
            <p className="text-sm text-gray-500">
              Factura {reminder.invoice_number} · {reminder.customer_name}
              {reminder.days_overdue > 0 && (
                <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700">
                  Vencida hace {reminder.days_overdue} días
                </span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={14}
          className="w-full rounded border border-gray-200 px-3 py-2 font-mono text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <p className="mt-2 text-xs text-gray-400">
          Puedes editar el texto antes de copiarlo. Este texto está listo para
          pegar en un email o WhatsApp.
        </p>

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cerrar
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copiado' : 'Copiar al portapapeles'}
          </button>
        </div>
      </div>
    </div>
  )
}
