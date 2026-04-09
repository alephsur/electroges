import { useState } from 'react'
import { useRegisterPayment } from '../hooks/use-payments'
import type { PaymentMethod } from '../types'

const METHOD_OPTIONS: { value: PaymentMethod; label: string }[] = [
  { value: 'transfer', label: 'Transferencia' },
  { value: 'cash', label: 'Efectivo' },
  { value: 'card', label: 'Tarjeta' },
  { value: 'direct_debit', label: 'Domiciliación' },
]

function today() {
  return new Date().toISOString().split('T')[0]
}

interface Props {
  invoiceId: string
  pendingAmount: number
  onSuccess: () => void
  onCancel: () => void
}

export function PaymentForm({
  invoiceId,
  pendingAmount,
  onSuccess,
  onCancel,
}: Props) {
  const [amount, setAmount] = useState(String(pendingAmount))
  const [date, setDate] = useState(today())
  const [method, setMethod] = useState<PaymentMethod>('transfer')
  const [reference, setReference] = useState('')
  const [notes] = useState('')

  const { mutate, isPending, error } = useRegisterPayment(invoiceId)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate(
      {
        amount: parseFloat(amount),
        payment_date: date,
        method,
        reference: reference || null,
        notes: notes || null,
      },
      { onSuccess },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Importe (€)
          </label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            max={pendingAmount}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Fecha de cobro
          </label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">
          Método de pago
        </label>
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value as PaymentMethod)}
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {METHOD_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">
          Referencia{' '}
          <span className="text-gray-400">(nº transferencia, etc.)</span>
        </label>
        <input
          type="text"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          placeholder="Opcional"
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {error && (
        <p className="text-xs text-red-600">
          {(error as any).response?.data?.detail ?? 'Error al registrar el cobro'}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="rounded bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {isPending ? 'Guardando…' : 'Registrar cobro'}
        </button>
      </div>
    </form>
  )
}
