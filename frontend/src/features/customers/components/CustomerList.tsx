import { Eye, Pencil, UserX } from 'lucide-react'
import { useCustomerStore } from '../store/customer-store'
import { useDeactivateCustomer } from '../hooks/use-customers'
import { CustomerTypeBadge } from './CustomerTypeBadge'
import type { CustomerSummary } from '../types'

interface CustomerListProps {
  customers: CustomerSummary[]
  total: number
  isLoading: boolean
}

export function CustomerList({ customers, total, isLoading }: CustomerListProps) {
  const { selectedCustomerId, setSelectedCustomerId } = useCustomerStore()
  const deactivate = useDeactivateCustomer()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
        Cargando clientes...
      </div>
    )
  }

  if (customers.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
        No se encontraron clientes.
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-500">{total} clientes</span>
      </div>
      <div className="divide-y divide-gray-50">
        {customers.map((customer) => {
          const isSelected = customer.id === selectedCustomerId
          return (
            <div
              key={customer.id}
              onClick={() => setSelectedCustomerId(customer.id)}
              className={`flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors ${
                isSelected ? 'bg-brand-50' : 'hover:bg-gray-50'
              }`}
            >
              {/* Avatar */}
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-full shrink-0 text-sm font-semibold ${
                  isSelected ? 'bg-brand-200 text-brand-800' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {customer.name.charAt(0).toUpperCase()}
              </div>

              {/* Name + type */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {customer.name}
                  </span>
                  <CustomerTypeBadge type={customer.customer_type} />
                  {!customer.is_active && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-400">
                      Inactivo
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  {customer.email && (
                    <span className="text-xs text-gray-400 truncate">{customer.email}</span>
                  )}
                  {customer.phone && (
                    <span className="text-xs text-gray-400">{customer.phone}</span>
                  )}
                </div>
              </div>

              {/* Location */}
              {customer.primary_address && (
                <div className="hidden lg:block text-xs text-gray-400 shrink-0">
                  {customer.primary_address.city}
                </div>
              )}

              {/* Activity + billing */}
              <div className="hidden xl:flex flex-col items-end gap-0.5 shrink-0 text-right">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
                      customer.active_work_orders > 0
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {customer.active_work_orders} obras
                  </span>
                </div>
                {customer.total_billed > 0 && (
                  <span className="text-xs text-emerald-600 font-medium">
                    {customer.total_billed.toLocaleString('es-ES', {
                      style: 'currency',
                      currency: 'EUR',
                      maximumFractionDigits: 0,
                    })}
                  </span>
                )}
                {customer.pending_amount > 0 && (
                  <span className="text-xs text-amber-600">
                    {customer.pending_amount.toLocaleString('es-ES', {
                      style: 'currency',
                      currency: 'EUR',
                      maximumFractionDigits: 0,
                    })}{' '}
                    pendiente
                  </span>
                )}
              </div>

              {/* Actions */}
              <div
                className="flex items-center gap-1 shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => setSelectedCustomerId(customer.id)}
                  title="Ver detalle"
                  className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"
                >
                  <Eye size={14} />
                </button>
                {customer.is_active && (
                  <button
                    onClick={() => {
                      if (confirm(`¿Desactivar el cliente "${customer.name}"?`))
                        deactivate.mutate(customer.id)
                    }}
                    title="Desactivar"
                    className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <UserX size={14} />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
