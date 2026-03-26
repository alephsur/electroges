import { useEffect, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { useInventoryItems } from '../hooks/use-inventory-items'
import { useInventoryStore } from '../store/inventory-store'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { InventoryList } from './InventoryList'
import { InventoryItemDetail } from './InventoryItemDetail'
import { InventoryItemForm } from './InventoryItemForm'

export function InventoryPage() {
  const {
    searchQuery,
    supplierFilter,
    lowStockOnly,
    selectedItemId,
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

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white shrink-0">
        <h1 className="text-lg font-semibold text-gray-900">Inventario</h1>
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Buscar material..."
              className="pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 w-52"
            />
          </div>

          {/* Low stock toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => setLowStockOnly(e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-600">Solo alertas</span>
          </label>

          {/* New item */}
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
          >
            <Plus size={14} />
            Nuevo material
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden p-6">
        {selectedItemId ? (
          /* Two-column layout when an item is selected */
          <div className="flex gap-5 h-full">
            <div className="flex-[3] min-w-0 overflow-y-auto">
              <InventoryList items={items} total={total} isLoading={isLoading} />
            </div>
            <div className="flex-[2] min-w-0 overflow-y-auto">
              <InventoryItemDetail />
            </div>
          </div>
        ) : (
          /* Full-width list */
          <InventoryList items={items} total={total} isLoading={isLoading} />
        )}
      </div>

      {showCreateForm && (
        <InventoryItemForm onClose={() => setShowCreateForm(false)} />
      )}
    </div>
  )
}
