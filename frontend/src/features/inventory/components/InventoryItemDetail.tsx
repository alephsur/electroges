import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Info, ArrowLeft } from 'lucide-react'
import { useInventoryItem, useUpdateInventoryItem } from '../hooks/use-inventory-items'
import { SupplierPriceList } from './SupplierPriceList'
import { StockAdjustmentForm } from './StockAdjustmentForm'
import { MovementHistory } from './MovementHistory'
import { useInventoryStore } from '../store/inventory-store'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { cn } from '@/shared/utils/cn'

const UNIT_OPTIONS = ['ud', 'm', 'm²', 'm³', 'kg', 'l', 'caja', 'rollo', 'bobina', 'par']

type Tab = 'ficha' | 'stock' | 'proveedores' | 'movimientos'

const TABS: { key: Tab; label: string }[] = [
  { key: 'ficha', label: 'Ficha' },
  { key: 'proveedores', label: 'Proveedores' },
  { key: 'stock', label: 'Stock' },
  { key: 'movimientos', label: 'Movimientos' },
]

interface InventoryItemDetailProps {
  itemId: string
}

export function InventoryItemDetail({ itemId }: InventoryItemDetailProps) {
  const navigate = useNavigate()
  const activeTab = useInventoryStore((s) => s.activeTab) as Tab
  const setActiveTab = useInventoryStore((s) => s.setActiveTab)

  const { data: item, isLoading, error } = useInventoryItem(itemId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Cargando...
      </div>
    )
  }

  if (error || !item) {
    return (
      <div className="p-6 text-sm text-red-500">
        {getApiErrorMessage(error) || 'No se pudo cargar el material'}
      </div>
    )
  }

  return (
    <div className="flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden h-full">
      {/* Mobile back button */}
      <button
        onClick={() => navigate('/inventario')}
        className="flex items-center gap-1.5 px-5 pt-3 pb-1 text-sm text-gray-500 hover:text-gray-700 lg:hidden"
      >
        <ArrowLeft size={14} />
        Inventario
      </button>

      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-gray-100">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{item.name}</h3>
          {item.description && (
            <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
          )}
        </div>
        <button
          onClick={() => navigate('/inventario')}
          className="text-gray-400 hover:text-gray-600 mt-0.5"
        >
          <X size={16} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100 px-4">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              'px-3 py-2.5 text-xs font-medium border-b-2 transition-colors',
              activeTab === key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-gray-500 hover:text-gray-700',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {activeTab === 'ficha' && <FichaTab item={item} />}
        {activeTab === 'proveedores' && <SupplierPriceList item={item} />}
        {activeTab === 'stock' && <StockTab item={item} />}
        {activeTab === 'movimientos' && (
          <MovementHistory itemId={item.id} unit={item.unit} />
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ tab: ficha

function FichaTab({ item }: { item: NonNullable<ReturnType<typeof useInventoryItem>['data']> }) {
  const [name, setName] = useState(item.name)
  const [description, setDescription] = useState(item.description ?? '')
  const [unit, setUnit] = useState(item.unit)
  const [unitPrice, setUnitPrice] = useState(String(item.unit_price))
  const [stockMin, setStockMin] = useState(String(item.stock_min))
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const updateMutation = useUpdateInventoryItem()

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaveError(null)
    setSaved(false)
    try {
      await updateMutation.mutateAsync({
        id: item.id,
        name: name.trim(),
        description: description.trim() || null,
        unit,
        unit_price: parseFloat(unitPrice) || 0,
        stock_min: parseFloat(stockMin) || 0,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setSaveError(getApiErrorMessage(err))
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <div>
        <label className="block text-xs text-gray-500 mb-1">
          Nombre <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Descripción</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unidad</label>
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {UNIT_OPTIONS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">P. venta (€)</label>
          <input
            type="number"
            step="0.0001"
            min="0"
            value={unitPrice}
            onChange={(e) => setUnitPrice(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Stock mín.</label>
          <input
            type="number"
            step="0.001"
            min="0"
            value={stockMin}
            onChange={(e) => setStockMin(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* PMP — readonly with tooltip */}
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <label className="text-xs text-gray-500">Precio medio de coste (PMP)</label>
          <span
            title="El Precio Medio Ponderado se calcula automáticamente en base a todas las entradas de stock registradas. No es editable directamente."
            className="cursor-help"
          >
            <Info size={12} className="text-gray-400" />
          </span>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700">
          {Number(item.unit_cost_avg).toLocaleString('es-ES', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 4,
          })}{' '}
          / {item.unit}
        </div>
      </div>

      {saveError && <p className="text-xs text-red-600">{saveError}</p>}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50"
        >
          {updateMutation.isPending ? 'Guardando...' : 'Guardar'}
        </button>
        {saved && <span className="text-xs text-green-600">Guardado</span>}
      </div>
    </form>
  )
}

// ------------------------------------------------------------------ tab: stock

function StockTab({ item }: { item: NonNullable<ReturnType<typeof useInventoryItem>['data']> }) {
  const stockAvailable = Number(item.stock_available)
  const stockMin = Number(item.stock_min)
  const isAlert = item.low_stock_alert

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-3">
        <MetricCard
          label="Stock actual"
          value={Number(item.stock_current)}
          unit={item.unit}
          color="text-gray-900"
        />
        <MetricCard
          label="Reservado"
          value={Number(item.stock_reserved)}
          unit={item.unit}
          color="text-gray-400"
          badge="Pendiente obras"
        />
        <MetricCard
          label="Disponible"
          value={stockAvailable}
          unit={item.unit}
          color={isAlert ? 'text-red-600' : stockAvailable <= stockMin * 1.5 ? 'text-amber-600' : 'text-green-700'}
        />
      </div>

      <div className="border-t border-gray-100 pt-5">
        <StockAdjustmentForm itemId={item.id} unit={item.unit} />
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  unit,
  color,
  badge,
}: {
  label: string
  value: number
  unit: string
  color: string
  badge?: string
}) {
  const isInteger = Number.isInteger(value)
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={cn('text-2xl font-bold tabular-nums', color)}>
        {isInteger
          ? value.toLocaleString('es-ES')
          : value.toLocaleString('es-ES', { maximumFractionDigits: 3 })}
      </p>
      <p className="text-xs text-gray-400 mt-0.5">{unit}</p>
      {badge && (
        <span className="mt-1 inline-block text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded-full">
          {badge}
        </span>
      )}
    </div>
  )
}
