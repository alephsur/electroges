import { useState, useRef, useEffect } from 'react'
import { Search, Package, Plus, X, Check, AlertTriangle } from 'lucide-react'
import { useInventoryItems, useCreateInventoryItem } from '@/features/inventory/hooks/use-inventory-items'
import type { InventoryItem } from '@/features/inventory/types'

interface InventoryItemPickerProps {
  value: InventoryItem | null
  onChange: (item: InventoryItem | null) => void
  placeholder?: string
  required?: boolean
}

interface CreateFormState {
  name: string
  unit: string
  unit_cost: string
  unit_price: string
}

function fmt(n: number) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function InventoryItemPicker({
  value,
  onChange,
  placeholder,
  required,
}: InventoryItemPickerProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [createForm, setCreateForm] = useState<CreateFormState>({
    name: '',
    unit: 'ud',
    unit_cost: '',
    unit_price: '',
  })

  const containerRef = useRef<HTMLDivElement>(null)
  const createItem = useCreateInventoryItem()

  const { data, isLoading } = useInventoryItems({ q: query || undefined, limit: 20 })
  const items = data?.items ?? []

  useEffect(() => {
    function handleOutsideClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  const handleSelect = (item: InventoryItem) => {
    onChange(item)
    setQuery('')
    setIsOpen(false)
    setIsCreating(false)
  }

  const handleClear = () => {
    onChange(null)
    setQuery('')
  }

  const handleStartCreate = () => {
    setIsOpen(false)
    setIsCreating(true)
    setCreateForm({ name: query.trim(), unit: 'ud', unit_cost: '', unit_price: '' })
  }

  const handleCreate = async () => {
    if (!createForm.name.trim()) return
    try {
      const newItem = await createItem.mutateAsync({
        name: createForm.name.trim(),
        unit: createForm.unit || 'ud',
        unit_cost: createForm.unit_cost ? parseFloat(createForm.unit_cost) : undefined,
        unit_price: createForm.unit_price ? parseFloat(createForm.unit_price) : undefined,
      })
      onChange(newItem)
      setIsCreating(false)
      setQuery('')
    } catch {
      // error handled by caller context
    }
  }

  // ── Selected state ────────────────────────────────────────────────────────────

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Package size={14} className="shrink-0 text-blue-500" />
          <span className="truncate font-medium text-blue-800">{value.name}</span>
          <span className="shrink-0 text-xs text-blue-500">
            {value.unit} · {fmt(Number(value.unit_cost_avg || 0))} €/ud
          </span>
          {value.low_stock_alert && (
            <AlertTriangle size={12} className="shrink-0 text-amber-500" aria-label="Stock bajo mínimo" />
          )}
        </div>
        <button
          type="button"
          onClick={handleClear}
          className="ml-2 shrink-0 text-blue-400 hover:text-blue-600"
          title="Quitar selección"
        >
          <X size={14} />
        </button>
      </div>
    )
  }

  // ── Inline create form ────────────────────────────────────────────────────────

  if (isCreating) {
    return (
      <div className="space-y-2 rounded-md border border-dashed border-green-400 bg-green-50 p-3">
        <p className="text-xs font-semibold text-green-700">Crear nuevo material en inventario</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="col-span-2">
            <input
              autoFocus
              value={createForm.name}
              onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Nombre del material *"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate()
                if (e.key === 'Escape') setIsCreating(false)
              }}
            />
          </div>
          <div>
            <input
              value={createForm.unit}
              onChange={(e) => setCreateForm((f) => ({ ...f, unit: e.target.value }))}
              placeholder="Unidad (ud, m, kg…)"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
            />
          </div>
          <div>
            <input
              value={createForm.unit_cost}
              onChange={(e) => setCreateForm((f) => ({ ...f, unit_cost: e.target.value }))}
              type="number"
              step="0.0001"
              min="0"
              placeholder="Coste unitario €"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
            />
          </div>
          <div>
            <input
              value={createForm.unit_price}
              onChange={(e) => setCreateForm((f) => ({ ...f, unit_price: e.target.value }))}
              type="number"
              step="0.0001"
              min="0"
              placeholder="Precio venta €"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-green-500"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleCreate}
            disabled={!createForm.name.trim() || createItem.isPending}
            className="flex items-center gap-1.5 rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            <Check size={12} />
            {createItem.isPending ? 'Creando…' : 'Crear y seleccionar'}
          </button>
          <button
            type="button"
            onClick={() => setIsCreating(false)}
            className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  // ── Search combobox ───────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder ?? 'Buscar en inventario…'}
          className="w-full rounded-md border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {required && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-red-400">*</span>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg">
          <div className="max-h-48 overflow-y-auto">
            {isLoading ? (
              <div className="px-3 py-2 text-xs text-gray-400">Buscando…</div>
            ) : items.length > 0 ? (
              items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelect(item)
                  }}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-blue-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-gray-800 truncate">{item.name}</span>
                      {item.low_stock_alert && (
                        <AlertTriangle size={11} className="shrink-0 text-amber-500" />
                      )}
                    </div>
                    {item.description && (
                      <div className="truncate text-xs text-gray-400">{item.description}</div>
                    )}
                  </div>
                  <div className="ml-3 shrink-0 text-right">
                    <div className="text-xs font-medium text-gray-600">
                      {fmt(Number(item.unit_price))} €/{item.unit}
                    </div>
                    <div className="text-xs text-gray-400">Stock: {item.stock_available}</div>
                  </div>
                </button>
              ))
            ) : query ? (
              <div className="px-3 py-2 text-xs text-gray-400">Sin resultados para "{query}"</div>
            ) : (
              <div className="px-3 py-2 text-xs text-gray-400">Escribe para buscar…</div>
            )}
          </div>

          {query.trim() && (
            <div className="border-t border-gray-100">
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  handleStartCreate()
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-green-700 hover:bg-green-50"
              >
                <Plus size={13} className="shrink-0" />
                <span>
                  Crear nuevo:{' '}
                  <span className="font-medium">"{query.trim()}"</span>
                </span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
