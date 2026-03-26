import { useState } from 'react'
import { X } from 'lucide-react'
import { useCustomers } from '@/features/customers/hooks/use-customers'
import { useLinkCustomer } from '../hooks/use-site-visits'
import type { SiteVisit } from '../types'

interface LinkCustomerModalProps {
  visit: SiteVisit
  onClose: () => void
}

export function LinkCustomerModal({ visit, onClose }: LinkCustomerModalProps) {
  const [search, setSearch] = useState('')
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)

  const { data: customersData } = useCustomers({ q: search || undefined, limit: 20 })
  const linkCustomer = useLinkCustomer()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCustomerId) return
    linkCustomer.mutate(
      { visitId: visit.id, customerId: selectedCustomerId },
      { onSuccess: onClose },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Vincular cliente</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Buscar cliente
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setSelectedCustomerId(null)
              }}
              placeholder="Nombre, NIF, email..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {customersData && customersData.items.length > 0 && (
            <div className="max-h-48 divide-y divide-gray-100 overflow-y-auto rounded-md border border-gray-200">
              {customersData.items.map((customer) => (
                <button
                  key={customer.id}
                  type="button"
                  onClick={() => setSelectedCustomerId(customer.id)}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                    selectedCustomerId === customer.id
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-900'
                  }`}
                >
                  <span className="font-medium">{customer.name}</span>
                  {customer.tax_id && (
                    <span className="ml-2 text-xs text-gray-400">{customer.tax_id}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedCustomerId && (
            <p className="text-sm text-green-700">
              Cliente seleccionado. Confirma para vincularlo a esta visita.
            </p>
          )}

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
              disabled={!selectedCustomerId || linkCustomer.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {linkCustomer.isPending ? 'Vinculando...' : 'Vincular cliente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
