import { useState } from 'react'
import { useManualAdjustment } from '../hooks/use-inventory-items'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'

interface StockAdjustmentFormProps {
  itemId: string
  unit: string
}

export function StockAdjustmentForm({ itemId, unit }: StockAdjustmentFormProps) {
  const [quantity, setQuantity] = useState('')
  const [unitCost, setUnitCost] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useManualAdjustment()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const qty = parseFloat(quantity)
    const cost = parseFloat(unitCost)

    if (isNaN(qty) || qty === 0) {
      setError('La cantidad no puede ser cero')
      return
    }
    if (isNaN(cost) || cost <= 0) {
      setError('El precio unitario debe ser mayor que cero')
      return
    }
    if (notes.trim().length < 5) {
      setError('Las notas deben tener al menos 5 caracteres')
      return
    }

    try {
      await mutation.mutateAsync({ itemId, quantity: qty, unit_cost: cost, notes: notes.trim() })
      setQuantity('')
      setUnitCost('')
      setNotes('')
    } catch (err) {
      setError(getApiErrorMessage(err))
    }
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Registrar movimiento de stock</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Cantidad ({unit}) — positivo entrada, negativo corrección
            </label>
            <input
              type="number"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="ej. 10 o -2"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Precio unitario (€)</label>
            <input
              type="number"
              step="0.0001"
              min="0.0001"
              value={unitCost}
              onChange={(e) => setUnitCost(e.target.value)}
              placeholder="ej. 3.50"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              required
            />
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Notas <span className="text-red-400">*</span>
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Motivo del ajuste (requerido para trazabilidad)"
            rows={2}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
            required
          />
        </div>

        {error && <p className="text-xs text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? 'Registrando...' : 'Registrar ajuste'}
        </button>
      </form>

      <p className="mt-4 text-xs text-gray-400">
        Las entradas por pedido a proveedor se registran automáticamente al marcar el pedido como
        recibido.
      </p>
    </div>
  )
}
