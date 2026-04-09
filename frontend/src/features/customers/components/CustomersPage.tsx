import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams } from 'react-router-dom'
import { Plus, Search, Users } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useCustomers, useCreateCustomer } from '../hooks/use-customers'
import { useCustomerStore, PAGE_SIZE_OPTIONS } from '../store/customer-store'
import type { PageSize } from '../store/customer-store'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { CustomerList } from './CustomerList'
import { CustomerDetail } from './CustomerDetail'
import { CustomerForm } from './CustomerForm'
import type { CustomerType } from '../types'

const TYPE_FILTER_OPTIONS: Array<{ value: CustomerType | ''; label: string }> = [
  { value: '', label: 'Todos' },
  { value: 'individual', label: 'Particulares' },
  { value: 'company', label: 'Empresas' },
  { value: 'community', label: 'Comunidades' },
]

function CustomerDetailRoute() {
  const { customerId } = useParams<{ customerId: string }>()
  const { setActiveTab } = useCustomerStore()

  useEffect(() => {
    setActiveTab('timeline')
  }, [customerId])

  if (!customerId) return null

  return <CustomerDetail customerId={customerId} />
}

export function CustomersPage() {
  const {
    searchQuery,
    typeFilter,
    showInactive,
    page,
    pageSize,
    setSearchQuery,
    setTypeFilter,
    setShowInactive,
    setPage,
    setPageSize,
  } = useCustomerStore()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [inputValue, setInputValue] = useState(searchQuery)
  const debouncedQuery = useDebounce(inputValue, 300)

  useEffect(() => {
    setSearchQuery(debouncedQuery)
  }, [debouncedQuery, setSearchQuery])

  const { data, isLoading } = useCustomers({
    q: searchQuery || undefined,
    customer_type: typeFilter ?? undefined,
    is_active: showInactive ? undefined : true,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  const createCustomer = useCreateCustomer()
  const customers = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  const detailMatch = useMatch('/clientes/:customerId')
  const isDetailSelected = !!detailMatch

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex flex-col min-w-0',
          isDetailSelected
            ? 'hidden lg:flex lg:w-[55%] lg:shrink-0 lg:border-r lg:border-gray-100'
            : 'flex flex-1',
        )}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Users size={18} className="text-gray-400" />
              <h1 className="text-lg font-semibold text-gray-900">Clientes</h1>
            </div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
            >
              <Plus size={14} />
              <span className="hidden sm:inline">Nuevo cliente</span>
              <span className="sm:hidden">Nuevo</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Buscar cliente..."
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50"
            />
          </div>

          {/* Filters row */}
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={typeFilter ?? ''}
              onChange={(e) =>
                setTypeFilter(e.target.value ? (e.target.value as CustomerType) : null)
              }
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            >
              {TYPE_FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-gray-600">Mostrar inactivos</span>
            </label>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4">
          <CustomerList customers={customers} total={total} isLoading={isLoading} />
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
          'flex-1 flex flex-col overflow-hidden min-w-0',
          !isDetailSelected && 'hidden lg:flex',
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center text-sm text-gray-400">
                Selecciona un cliente para ver el detalle
              </div>
            }
          />
          <Route path=":customerId" element={<CustomerDetailRoute />} />
        </Routes>
      </div>

      {/* Create modal */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Nuevo cliente</h2>
            <CustomerForm
              onSubmit={(data) =>
                createCustomer.mutate(data, { onSuccess: () => setShowCreateForm(false) })
              }
              onCancel={() => setShowCreateForm(false)}
              isLoading={createCustomer.isPending}
            />
          </div>
        </div>
      )}
    </div>
  )
}
