import { useState } from 'react'
import { useCreateRectification } from '../hooks/use-invoices'

interface Props {
  invoiceId: string
  invoiceNumber: string
  onSuccess: (newInvoiceId: string) => void
  onClose: () => void
}

export function RectificationModal({
  invoiceId,
  invoiceNumber,
  onSuccess,
  onClose,
}: Props) {
  const [reason, setReason] = useState('')
  const { mutate, isPending, error } = useCreateRectification()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate(
      { id: invoiceId, reason },
      { onSuccess: (data) => onSuccess(data.id) },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-lg font-semibold text-gray-800">
          Crear factura rectificativa
        </h2>
        <p className="mb-4 text-sm text-gray-500">
          La factura <strong>{invoiceNumber}</strong> será anulada y se creará una
          nueva rectificativa con los importes negativos.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">
              Motivo de la rectificación *
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={5}
              rows={3}
              placeholder="Describe el motivo de la rectificación…"
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="text-xs text-red-600">
              {(error as any).response?.data?.detail ?? 'Error al crear la rectificativa'}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending || reason.length < 5}
              className="rounded bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {isPending ? 'Creando…' : 'Crear rectificativa'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
