import { AlertTriangle, Pencil, SlidersHorizontal, PowerOff } from 'lucide-react'
import { useNavigate, useMatch } from 'react-router-dom'
import { useInventoryStore } from '../store/inventory-store'
import { useDeactivateInventoryItem } from '../hooks/use-inventory-items'
import { cn } from '@/shared/utils/cn'
import type { InventoryItem } from '../types'

interface InventoryListProps {
  items: InventoryItem[]
  total: number
  isLoading: boolean
}

export function InventoryList({ items, total, isLoading }: InventoryListProps) {
  const navigate = useNavigate()
  const match = useMatch('/inventario/:itemId')
  const selectedItemId = match?.params.itemId ?? null
  const { setActiveTab } = useInventoryStore()
  const deactivate = useDeactivateInventoryItem()

  const handleDeactivate = async (e: React.MouseEvent, item: InventoryItem) => {
    e.stopPropagation()
    if (!confirm(`¿Desactivar "${item.name}"?`)) return
    await deactivate.mutateAsync(item.id)
    if (selectedItemId === item.id) navigate('/inventario')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Cargando materiales...
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        No se encontraron materiales
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-100 text-xs text-gray-400">
        {total} material{total !== 1 ? 'es' : ''}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">
              <th className="px-4 py-3">Material</th>
              <th className="px-4 py-3">Unidad</th>
              <th className="hidden lg:table-cell px-4 py-3">Proveedor preferido</th>
              <th className="hidden md:table-cell px-4 py-3 text-right">P. coste medio</th>
              <th className="px-4 py-3 text-right">Stock dispon.</th>
              <th className="hidden md:table-cell px-4 py-3 text-right">Stock mín.</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {items.map((item) => (
              <InventoryRow
                key={item.id}
                item={item}
                isSelected={selectedItemId === item.id}
                onSelect={() => navigate(`/inventario/${item.id}`)}
                onAdjustStock={(e) => {
                  e.stopPropagation()
                  setActiveTab('stock')
                  navigate(`/inventario/${item.id}`)
                }}
                onDeactivate={handleDeactivate}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

interface InventoryRowProps {
  item: InventoryItem
  isSelected: boolean
  onSelect: () => void
  onAdjustStock: (e: React.MouseEvent) => void
  onDeactivate: (e: React.MouseEvent, item: InventoryItem) => void
}

function InventoryRow({
  item,
  isSelected,
  onSelect,
  onAdjustStock,
  onDeactivate,
}: InventoryRowProps) {
  const stockAvailable = Number(item.stock_available)
  const stockMin = Number(item.stock_min)
  const isAlert = item.low_stock_alert
  const isAmber = !isAlert && stockAvailable <= stockMin * 1.5

  const otherSuppliersCount = item.supplier_items.filter(
    (s) => s.is_active && !s.is_preferred,
  ).length

  return (
    <tr
      onClick={onSelect}
      className={cn(
        'cursor-pointer transition-colors',
        isSelected ? 'bg-brand-50' : 'hover:bg-gray-50',
      )}
    >
      <td className="px-4 py-3 max-w-[200px]">
        <p className="font-semibold text-gray-900 truncate">{item.name}</p>
        {item.description && (
          <p className="text-xs text-gray-400 truncate mt-0.5">{item.description}</p>
        )}
      </td>
      <td className="px-4 py-3 text-gray-500">{item.unit}</td>
      <td className="hidden lg:table-cell px-4 py-3">
        {item.preferred_supplier ? (
          <div className="flex items-center gap-1.5">
            <span className="inline-block px-2 py-0.5 bg-brand-50 text-brand-700 text-xs rounded-full font-medium">
              {item.preferred_supplier.supplier_name}
            </span>
            {otherSuppliersCount > 0 && (
              <span className="text-xs text-gray-400">+{otherSuppliersCount} más</span>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-300">Sin proveedor</span>
        )}
      </td>
      <td className="hidden md:table-cell px-4 py-3 text-right text-gray-700 font-mono text-xs">
        {Number(item.unit_cost_avg).toLocaleString('es-ES', {
          style: 'currency',
          currency: 'EUR',
          minimumFractionDigits: 4,
        })}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-1">
          {isAlert && <AlertTriangle size={12} className="text-red-500" />}
          <span
            className={cn(
              'font-semibold tabular-nums',
              isAlert ? 'text-red-600' : isAmber ? 'text-amber-600' : 'text-gray-700',
            )}
          >
            {stockAvailable.toLocaleString('es-ES', { maximumFractionDigits: 3 })}
          </span>
          {isAlert && (
            <span className="text-[10px] font-bold uppercase bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">
              REPONER
            </span>
          )}
        </div>
      </td>
      <td className="hidden md:table-cell px-4 py-3 text-right text-xs text-gray-500 tabular-nums">
        {stockMin.toLocaleString('es-ES', { maximumFractionDigits: 3 })}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={(e) => { e.stopPropagation(); onSelect() }}
            className="p-1 text-gray-400 hover:text-brand-600"
            title="Editar"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={onAdjustStock}
            className="p-1 text-gray-400 hover:text-brand-600"
            title="Ajustar stock"
          >
            <SlidersHorizontal size={13} />
          </button>
          <button
            onClick={(e) => onDeactivate(e, item)}
            className="p-1 text-gray-400 hover:text-red-600"
            title="Desactivar"
          >
            <PowerOff size={13} />
          </button>
        </div>
      </td>
    </tr>
  )
}
