import { useEffect, useState } from 'react'
import { Plus, Search, Users } from 'lucide-react'
import { useCustomers } from '../hooks/use-customers'
import { useCustomerStore } from '../store/customer-store'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { CustomerList } from './CustomerList'
import { CustomerDetail } from './CustomerDetail'
import { CustomerForm } from './CustomerForm'
import { useCreateCustomer } from '../hooks/use-customers'
import type { CustomerType } from '../types'

const TYPE_FILTER_OPTIONS: Array<{ value: CustomerType | ''; label: string }> = [
  { value: '', label: 'Todos' },
  { value: 'individual', label: 'Particulares' },
  { value: 'company', label: 'Empresas' },
  { value: 'community', label: 'Comunidades' },
]

export function CustomersPage() {
  const {
    searchQuery,
    typeFilter,
    showInactive,
    selectedCustomerId,
    setSearchQuery,
    setTypeFilter,
    setShowInactive,
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
    limit: 100,
  })

  const createCustomer = useCreateCustomer()

  const customers = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <Users size={18} className="text-gray-400" />
          <h1 className="text-lg font-semibold text-gray-900">Clientes</h1>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Buscar cliente..."
              className="pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 w-52"
            />
          </div>

          {/* Type filter */}
          <select
            value={typeFilter ?? ''}
            onChange={(e) =>
              setTypeFilter(e.target.value ? (e.target.value as CustomerType) : null)
            }
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          >
            {TYPE_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Show inactive toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-600">Mostrar inactivos</span>
          </label>

          {/* New customer */}
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
          >
            <Plus size={14} />
            Nuevo cliente
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden p-6">
        {selectedCustomerId ? (
          /* Two-column layout: 55 / 45 */
          <div className="flex gap-5 h-full">
            <div className="flex-[11] min-w-0 overflow-y-auto">
              <CustomerList customers={customers} total={total} isLoading={isLoading} />
            </div>
            <div className="flex-[9] min-w-0 overflow-y-auto">
              <CustomerDetail />
            </div>
          </div>
        ) : (
          /* Full-width list */
          <CustomerList customers={customers} total={total} isLoading={isLoading} />
        )}
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
