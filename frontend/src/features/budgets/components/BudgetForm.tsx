import { useState, useRef, useEffect } from 'react'
import { X, Search, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { CustomerListResponse, CustomerSummary } from '@/features/customers/types'
import { useCreateBudget } from '../hooks/use-budgets'

interface BudgetFormProps {
  customerId?: string
  customerName?: string
  onClose: () => void
}

export function BudgetForm({ customerId, customerName, onClose }: BudgetFormProps) {
  const createBudget = useCreateBudget()
  const navigate = useNavigate()

  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null)
  const [searchQuery, setSearchQuery] = useState(customerName ?? '')
  const [showDropdown, setShowDropdown] = useState(false)
  const [notes, setNotes] = useState('')
  const [clientNotes, setClientNotes] = useState('')
  const [discount, setDiscount] = useState('0')
  const [taxRate, setTaxRate] = useState('')
  const searchRef = useRef<HTMLDivElement>(null)

  // If customerId was passed in as prop, skip the search UI
  const isPresetCustomer = !!customerId

  const { data: searchResults } = useQuery({
    queryKey: ['customers', 'search', searchQuery],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerListResponse>('/api/v1/customers', {
        params: { q: searchQuery, limit: 8, is_active: true },
      })
      return data.items
    },
    enabled: !isPresetCustomer && searchQuery.length >= 1,
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const resolvedCustomerId = isPresetCustomer ? customerId : selectedCustomer?.id

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createBudget.mutate(
      {
        customer_id: resolvedCustomerId,
        discount_pct: parseFloat(discount) || 0,
        tax_rate: taxRate ? parseFloat(taxRate) : undefined,
        notes: notes || null,
        client_notes: clientNotes || null,
      },
      {
        onSuccess: (data) => {
          navigate(`/presupuestos/${data.id}`)
          onClose()
        },
      },
    )
  }

  const handleSelectCustomer = (customer: CustomerSummary) => {
    setSelectedCustomer(customer)
    setSearchQuery(customer.name)
    setShowDropdown(false)
  }

  const handleClearCustomer = () => {
    setSelectedCustomer(null)
    setSearchQuery('')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Nuevo presupuesto</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {/* Customer selector */}
          {isPresetCustomer ? (
            <div className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700 flex items-center gap-2">
              <User size={14} />
              Cliente: <strong>{customerName}</strong>
            </div>
          ) : (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Cliente
                <span className="ml-1 text-xs font-normal text-gray-400">(opcional)</span>
              </label>
              <div ref={searchRef} className="relative">
                {selectedCustomer ? (
                  <div className="flex items-center justify-between rounded-md border border-blue-400 bg-blue-50 px-3 py-2 text-sm">
                    <div className="flex items-center gap-2">
                      <User size={14} className="text-blue-500" />
                      <span className="font-medium text-blue-800">{selectedCustomer.name}</span>
                      {selectedCustomer.tax_id && (
                        <span className="text-xs text-blue-500">{selectedCustomer.tax_id}</span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleClearCustomer}
                      className="text-blue-400 hover:text-blue-600"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <Search
                      size={14}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                    />
                    <input
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value)
                        setShowDropdown(true)
                      }}
                      onFocus={() => setShowDropdown(true)}
                      placeholder="Buscar cliente por nombre, NIF..."
                      className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </>
                )}

                {showDropdown && !selectedCustomer && searchResults && searchResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-52 overflow-y-auto rounded-lg border border-gray-100 bg-white shadow-lg">
                    {searchResults.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => handleSelectCustomer(c)}
                        className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-gray-50"
                      >
                        <User size={14} className="shrink-0 text-gray-400" />
                        <div className="min-w-0">
                          <div className="font-medium text-gray-800 truncate">{c.name}</div>
                          {(c.tax_id || c.phone) && (
                            <div className="text-xs text-gray-400 truncate">
                              {[c.tax_id, c.phone].filter(Boolean).join(' · ')}
                            </div>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {showDropdown && !selectedCustomer && searchQuery.length >= 1 && searchResults?.length === 0 && (
                  <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-lg border border-gray-100 bg-white px-3 py-3 text-center text-sm text-gray-400 shadow-lg">
                    Sin resultados
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                IVA (%)
                <span className="ml-1 text-xs font-normal text-gray-400">vacío = por defecto</span>
              </label>
              <input
                value={taxRate}
                onChange={(e) => setTaxRate(e.target.value)}
                type="number"
                step="0.01"
                min="0"
                max="100"
                placeholder="21.00"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Descuento global (%)
              </label>
              <input
                value={discount}
                onChange={(e) => setDiscount(e.target.value)}
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Notas para el cliente
            </label>
            <textarea
              value={clientNotes}
              onChange={(e) => setClientNotes(e.target.value)}
              rows={2}
              placeholder="Texto que aparecerá en el PDF del presupuesto..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-700">
              Notas internas
              <span className="text-xs font-normal text-amber-600">(solo interno)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Notas no visibles en el PDF..."
              className="w-full rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createBudget.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createBudget.isPending ? 'Creando...' : 'Crear presupuesto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
