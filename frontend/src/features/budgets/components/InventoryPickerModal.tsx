import { useState } from 'react'
import { X, Search, Package, AlertTriangle } from 'lucide-react'
import { useInventoryItems } from '@/features/inventory/hooks/use-inventory-items'
import type { InventoryItem } from '@/features/inventory/types'

interface InventoryPickerModalProps {
  onSelect: (item: InventoryItem) => void
  onClose: () => void
}

export function InventoryPickerModal({ onSelect, onClose }: InventoryPickerModalProps) {
  const [query, setQuery] = useState('')

  const { data, isLoading } = useInventoryItems({
    q: query || undefined,
    limit: 50,
  })

  const items = data?.items ?? []

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
      <div className="flex w-full max-w-lg flex-col rounded-xl bg-white shadow-2xl" style={{ maxHeight: '80vh' }}>
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-5 py-4">
          <div className="flex items-center gap-2">
            <Package size={16} className="text-gray-500" />
            <h2 className="text-base font-semibold text-gray-900">Seleccionar material del inventario</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        {/* Search */}
        <div className="shrink-0 border-b border-gray-100 px-5 py-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nombre..."
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-gray-400">Cargando...</div>
          ) : items.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">
              {query ? 'Sin resultados para esa búsqueda' : 'No hay ítems en el inventario'}
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelect(item)}
                  className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-blue-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800 truncate">{item.name}</span>
                      {item.low_stock_alert && (
                        <AlertTriangle size={12} className="shrink-0 text-amber-500" />
                      )}
                    </div>
                    {item.description && (
                      <div className="mt-0.5 text-xs text-gray-400 truncate">{item.description}</div>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-medium text-gray-700">
                      {Number(item.unit_price).toLocaleString('es-ES', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{' '}
                      €/{item.unit}
                    </div>
                    <div className="text-xs text-gray-400">
                      Stock: {item.stock_available} {item.unit}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
