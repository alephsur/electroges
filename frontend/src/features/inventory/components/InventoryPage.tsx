import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { apiClient } from '@/lib/api-client'
import { useInventoryItems } from '../hooks/use-inventory-items'
import { useInventoryStore, PAGE_SIZE_OPTIONS } from '../store/inventory-store'
import type { PageSize } from '../store/inventory-store'
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
  const navigate = useNavigate()
  const {
    searchQuery,
    supplierFilter,
    lowStockOnly,
    page,
    pageSize,
    setSearchQuery,
    setSupplierFilter,
    setLowStockOnly,
    setPage,
    setPageSize,
  } = useInventoryStore()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [inputValue, setInputValue] = useState(searchQuery)
  const debouncedQuery = useDebounce(inputValue, 300)

  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers', 'active-compact'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: { id: string; name: string }[] }>(
        '/api/v1/suppliers',
        { params: { is_active: true, limit: 200 } },
      )
      return data
    },
  })
  const supplierOptions = suppliersData?.items ?? []

  useEffect(() => {
    setSearchQuery(debouncedQuery)
  }, [debouncedQuery, setSearchQuery])

  const { data, isLoading } = useInventoryItems({
    q: searchQuery || undefined,
    supplier_id: supplierFilter ?? undefined,
    low_stock_only: lowStockOnly || undefined,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

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
            {supplierOptions.length > 0 && (
              <select
                value={supplierFilter ?? ''}
                onChange={(e) => setSupplierFilter(e.target.value || null)}
                className="border border-gray-200 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50 text-gray-600 shrink-0"
              >
                <option value="">Todos los proveedores</option>
                {supplierOptions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
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

        {/* Pagination */}
        {!isLoading && data && data.total > 0 && (
          <div className="shrink-0 border-t border-gray-100 px-4 py-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span>Por página:</span>
              {PAGE_SIZE_OPTIONS.map((size) => (
                <button
                  key={size}
                  onClick={() => setPageSize(size as PageSize)}
                  className={`rounded px-2 py-0.5 font-medium transition-colors ${
                    pageSize === size
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, data.total)} de {data.total}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ›
                </button>
              </div>
            </div>
          </div>
        )}
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
        <InventoryItemForm
          onClose={() => setShowCreateForm(false)}
          onCreated={(id) => {
            setShowCreateForm(false)
            navigate(`/inventario/${id}`)
          }}
        />
      )}
    </div>
  )
}
