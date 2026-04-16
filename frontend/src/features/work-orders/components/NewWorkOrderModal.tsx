import { useState, useRef, useEffect } from 'react'
import { X, Search, User, UserPlus, ChevronLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { CustomerListResponse, CustomerSummary } from '@/features/customers/types'
import { useCreateCustomer } from '@/features/customers/hooks/use-customers'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useCreateWorkOrder } from '../hooks/use-work-orders'

interface NewWorkOrderModalProps {
  onClose: () => void
  onCreated: (workOrderId: string) => void
}

export function NewWorkOrderModal({ onClose, onCreated }: NewWorkOrderModalProps) {
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [showQuickCreate, setShowQuickCreate] = useState(false)
  const [address, setAddress] = useState('')
  const [notes, setNotes] = useState('')
  const searchRef = useRef<HTMLDivElement>(null)

  // Quick-create customer fields
  const [quickName, setQuickName] = useState('')
  const [quickPhone, setQuickPhone] = useState('')
  const [quickEmail, setQuickEmail] = useState('')
  const [quickTaxId, setQuickTaxId] = useState('')

  const createCustomer = useCreateCustomer()
  const createWorkOrder = useCreateWorkOrder()

  const { data: searchResults } = useQuery({
    queryKey: ['customers', 'search', searchQuery],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerListResponse>('/api/v1/customers', {
        params: { q: searchQuery, limit: 8, is_active: true },
      })
      return data.items
    },
    enabled: searchQuery.length >= 1,
  })

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCustomer) return
    try {
      const workOrder = await createWorkOrder.mutateAsync({
        customer_id: selectedCustomer.id,
        address: address.trim() || undefined,
        notes: notes.trim() || undefined,
      })
      onCreated(workOrder.id)
    } catch (err) {
      alert(getApiErrorMessage(err))
    }
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

  const handleOpenQuickCreate = () => {
    setQuickName(searchQuery)
    setShowDropdown(false)
    setShowQuickCreate(true)
  }

  const handleQuickCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!quickName.trim()) return
    createCustomer.mutate(
      {
        customer_type: 'individual',
        name: quickName.trim(),
        phone: quickPhone.trim() || null,
        email: quickEmail.trim() || null,
        tax_id: quickTaxId.trim() || null,
      },
      {
        onSuccess: (newCustomer) => {
          setSelectedCustomer(newCustomer)
          setSearchQuery(newCustomer.name)
          setShowQuickCreate(false)
        },
      },
    )
  }

  const handleCancelQuickCreate = () => {
    setShowQuickCreate(false)
    setQuickName('')
    setQuickPhone('')
    setQuickEmail('')
    setQuickTaxId('')
  }

  const noResults =
    showDropdown && !selectedCustomer && searchQuery.length >= 1 && searchResults?.length === 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Nueva obra</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        {/* Quick-create customer panel */}
        {showQuickCreate ? (
          <form onSubmit={handleQuickCreate} className="space-y-4 px-6 py-4">
            <div className="mb-1 flex items-center gap-2">
              <button
                type="button"
                onClick={handleCancelQuickCreate}
                className="text-gray-400 hover:text-gray-600"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm font-medium text-gray-700">Nuevo cliente</span>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Nombre <span className="text-red-500">*</span>
              </label>
              <input
                value={quickName}
                onChange={(e) => setQuickName(e.target.value)}
                required
                autoFocus
                placeholder="Nombre y apellidos o razón social"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Teléfono</label>
                <input
                  value={quickPhone}
                  onChange={(e) => setQuickPhone(e.target.value)}
                  type="tel"
                  placeholder="600 000 000"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">NIF / CIF</label>
                <input
                  value={quickTaxId}
                  onChange={(e) => setQuickTaxId(e.target.value)}
                  placeholder="12345678A"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
              <input
                value={quickEmail}
                onChange={(e) => setQuickEmail(e.target.value)}
                type="email"
                placeholder="cliente@ejemplo.com"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={handleCancelQuickCreate}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createCustomer.isPending || !quickName.trim()}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createCustomer.isPending ? 'Creando...' : 'Crear cliente'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
            {/* Customer selector */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Cliente <span className="text-red-500">*</span>
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
                      autoFocus
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
                          <div className="truncate font-medium text-gray-800">{c.name}</div>
                          {(c.tax_id || c.phone) && (
                            <div className="truncate text-xs text-gray-400">
                              {[c.tax_id, c.phone].filter(Boolean).join(' · ')}
                            </div>
                          )}
                        </div>
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={handleOpenQuickCreate}
                      className="flex w-full items-center gap-2 border-t border-gray-100 px-3 py-2.5 text-left text-sm text-blue-600 hover:bg-blue-50"
                    >
                      <UserPlus size={14} />
                      Crear nuevo cliente
                    </button>
                  </div>
                )}

                {noResults && (
                  <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-lg border border-gray-100 bg-white shadow-lg">
                    <div className="px-3 py-3 text-center text-sm text-gray-400">
                      Sin resultados para "{searchQuery}"
                    </div>
                    <button
                      type="button"
                      onClick={handleOpenQuickCreate}
                      className="flex w-full items-center gap-2 border-t border-gray-100 px-3 py-2.5 text-left text-sm text-blue-600 hover:bg-blue-50"
                    >
                      <UserPlus size={14} />
                      Crear "{searchQuery}" como nuevo cliente
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Address */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Dirección de la obra
              </label>
              <input
                type="text"
                placeholder="Dirección (opcional)"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Notas</label>
              <textarea
                placeholder="Notas iniciales (opcional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                disabled={!selectedCustomer || createWorkOrder.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createWorkOrder.isPending ? 'Creando...' : 'Crear obra'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
