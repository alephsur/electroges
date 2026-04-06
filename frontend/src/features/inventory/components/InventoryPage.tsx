import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useInventoryItems } from '../hooks/use-inventory-items'
import { useInventoryStore } from '../store/inventory-store'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { InventoryList } from './InventoryList'
import { InventoryItemDetail } from './InventoryItemDetail'
import { InventoryItemForm } from './InventoryItemForm'

function InventoryItemDetailRoute() {
  const { itemId } = useParams<{ itemId: string }>()
  const { setActiveTab } = useInventoryStore()

  useEffect(() => {
    setActiveTab('ficha')
  }, [itemId])

  if (!itemId) return null
  return <InventoryItemDetail itemId={itemId} />
}

export function InventoryPage() {
  const {
    searchQuery,
    supplierFilter,
    lowStockOnly,
    setSearchQuery,
    setLowStockOnly,
  } = useInventoryStore()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [inputValue, setInputValue] = useState(searchQuery)
  const debouncedQuery = useDebounce(inputValue, 300)

  useEffect(() => {
    setSearchQuery(debouncedQuery)
  }, [debouncedQuery, setSearchQuery])

  const { data, isLoading } = useInventoryItems({
    q: searchQuery || undefined,
    supplier_id: supplierFilter ?? undefined,
    low_stock_only: lowStockOnly || undefined,
    limit: 100,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0

  const detailMatch = useMatch('/inventario/:itemId')
  const isDetailSelected = !!detailMatch

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex flex-col min-w-0',
          isDetailSelected
            ? 'hidden lg:flex lg:flex-1 lg:border-r lg:border-gray-100'
            : 'flex flex-1',
        )}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 p-4">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-lg font-semibold text-gray-900">Inventario</h1>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
            >
              <Plus size={14} />
              <span className="hidden sm:inline">Nuevo material</span>
              <span className="sm:hidden">Nuevo</span>
            </button>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-0">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Buscar material..."
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={lowStockOnly}
                onChange={(e) => setLowStockOnly(e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-600">Solo alertas</span>
            </label>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-auto p-4">
          <InventoryList items={items} total={total} isLoading={isLoading} />
        </div>
      </div>

      {/* Right panel — detail via nested routes */}
      <div
        className={cn(
          'flex flex-col overflow-hidden min-w-0 lg:w-[420px] lg:shrink-0',
          !isDetailSelected && 'hidden lg:flex',
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center text-sm text-gray-400 p-6 text-center">
                Selecciona un material para ver el detalle
              </div>
            }
          />
          <Route path=":itemId" element={<InventoryItemDetailRoute />} />
        </Routes>
      </div>

      {showCreateForm && (
        <InventoryItemForm onClose={() => setShowCreateForm(false)} />
      )}
    </div>
  )
}
