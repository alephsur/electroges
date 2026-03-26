import { AlertTriangle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useInventoryStore } from '../store/inventory-store'
import type { InventoryItem } from '../types'

interface LowStockBadgeProps {
  items: InventoryItem[]
  maxItems?: number
}

export function LowStockBadge({ items, maxItems = 5 }: LowStockBadgeProps) {
  const navigate = useNavigate()
  const setSelectedItemId = useInventoryStore((s) => s.setSelectedItemId)
  const visible = items.slice(0, maxItems)

  if (items.length === 0) return null

  const handleItemClick = (id: string) => {
    setSelectedItemId(id)
    navigate('/inventario')
  }

  return (
    <div className="bg-white border border-red-200 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-red-100 bg-red-50">
        <AlertTriangle size={14} className="text-red-600" />
        <span className="text-sm font-medium text-red-700">
          Stock bajo mínimos ({items.length})
        </span>
      </div>
      <ul className="divide-y divide-gray-50">
        {visible.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => handleItemClick(item.id)}
              className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 text-left"
            >
              <div>
                <p className="text-sm font-medium text-gray-900">{item.name}</p>
                {item.preferred_supplier && (
                  <span className="text-xs text-gray-400">{item.preferred_supplier.supplier_name}</span>
                )}
              </div>
              <div className="text-right ml-4">
                <span className="text-sm font-semibold text-red-600">
                  {Number(item.stock_current).toLocaleString('es-ES', { maximumFractionDigits: 3 })}
                </span>
                <span className="text-xs text-gray-400 ml-1">
                  / {Number(item.stock_min).toLocaleString('es-ES', { maximumFractionDigits: 3 })} {item.unit}
                </span>
              </div>
            </button>
          </li>
        ))}
      </ul>
      {items.length > maxItems && (
        <div className="px-4 py-2 border-t border-gray-100">
          <button
            onClick={() => navigate('/inventario')}
            className="text-xs text-brand-600 hover:text-brand-800 font-medium"
          >
            Ver inventario completo →
          </button>
        </div>
      )}
    </div>
  )
}
