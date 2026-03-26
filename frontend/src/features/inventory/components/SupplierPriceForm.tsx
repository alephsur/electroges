import { useState } from 'react'
import { X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useAddSupplierToItem } from '../hooks/use-supplier-items'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'

interface Supplier {
  id: string
  name: string
  is_active: boolean
}

interface SupplierListResponse {
  items: Supplier[]
  total: number
}

interface SupplierPriceFormProps {
  itemId: string
  onClose: () => void
}

export function SupplierPriceForm({ itemId, onClose }: SupplierPriceFormProps) {
  const [supplierId, setSupplierId] = useState('')
  const [supplierRef, setSupplierRef] = useState('')
  const [unitCost, setUnitCost] = useState('')
  const [leadTimeDays, setLeadTimeDays] = useState('')
  const [isPreferred, setIsPreferred] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useAddSupplierToItem(itemId)

  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers', 'active'],
    queryFn: async () => {
      const { data } = await apiClient.get<SupplierListResponse>('/api/v1/suppliers', {
        params: { is_active: true, limit: 200 },
      })
      return data
    },
  })

  const suppliers = suppliersData?.items ?? []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const cost = parseFloat(unitCost)
    if (!supplierId) {
      setError('Selecciona un proveedor')
      return
    }
    if (isNaN(cost) || cost <= 0) {
      setError('El precio unitario debe ser mayor que cero')
      return
    }

    try {
      await mutation.mutateAsync({
        supplier_id: supplierId,
        inventory_item_id: itemId,
        unit_cost: cost,
        supplier_ref: supplierRef || null,
        lead_time_days: leadTimeDays ? parseInt(leadTimeDays) : null,
        is_preferred: isPreferred,
      })
      onClose()
    } catch (err) {
      setError(getApiErrorMessage(err))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Añadir proveedor</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Proveedor <span className="text-red-400">*</span>
            </label>
            <select
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              required
            >
              <option value="">Selecciona un proveedor...</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Referencia del proveedor</label>
            <input
              type="text"
              value={supplierRef}
              onChange={(e) => setSupplierRef(e.target.value)}
              placeholder="Código o referencia interna del proveedor"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Precio unitario (€) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                step="0.0001"
                min="0.0001"
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                placeholder="0.00"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Plazo de entrega (días)</label>
              <input
                type="number"
                min="1"
                value={leadTimeDays}
                onChange={(e) => setLeadTimeDays(e.target.value)}
                placeholder="ej. 7"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isPreferred}
              onChange={(e) => setIsPreferred(e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-700">Marcar como proveedor preferido</span>
          </label>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Guardando...' : 'Añadir proveedor'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
