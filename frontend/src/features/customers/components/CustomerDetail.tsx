import { useState } from 'react'
import { X, Pencil, Calendar } from 'lucide-react'
import { useCustomer, useUpdateCustomer } from '../hooks/use-customers'
import { useCustomerStore } from '../store/customer-store'
import { CustomerTypeBadge } from './CustomerTypeBadge'
import { CustomerTimeline } from './CustomerTimeline'
import { CustomerAddressList } from './CustomerAddressList'
import { CustomerDocumentList } from './CustomerDocumentList'
import { CustomerForm } from './CustomerForm'
import type { CustomerUpdatePayload } from '../types'

export function CustomerDetail() {
  const { selectedCustomerId, setSelectedCustomerId, activeTab, setActiveTab } = useCustomerStore()
  const { data: customer, isLoading } = useCustomer(selectedCustomerId)
  const updateCustomer = useUpdateCustomer()
  const [editingFicha, setEditingFicha] = useState(false)

  if (!selectedCustomerId) return null

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 flex items-center justify-center h-full">
        <span className="text-sm text-gray-400">Cargando...</span>
      </div>
    )
  }

  if (!customer) return null

  const TABS = [
    { id: 'timeline', label: 'Actividad' },
    { id: 'ficha', label: 'Ficha' },
    { id: 'direcciones', label: 'Direcciones' },
    { id: 'documentos', label: 'Documentos' },
  ] as const

  return (
    <div className="bg-white border border-gray-200 rounded-xl flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-100 shrink-0">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xl font-bold shrink-0">
              {customer.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-semibold text-gray-900">{customer.name}</h2>
                <CustomerTypeBadge type={customer.customer_type} />
                {!customer.is_active && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                    Inactivo
                  </span>
                )}
              </div>
              {customer.contact_person && (
                <p className="text-xs text-gray-500 mt-0.5">Contacto: {customer.contact_person}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setActiveTab('ficha')}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Pencil size={12} />
              Editar
            </button>
            <button
              disabled
              title="Próximamente"
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-300 border border-gray-200 rounded-lg cursor-not-allowed"
            >
              <Calendar size={12} />
              Nueva visita
            </button>
            <button
              onClick={() => setSelectedCustomerId(null)}
              className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Metrics row */}
        <div className="mt-3 flex items-center gap-4">
          <div className="text-center">
            <p className="text-lg font-semibold text-gray-900">{customer.active_work_orders}</p>
            <p className="text-xs text-gray-400">Obras activas</p>
          </div>
          <div className="h-8 w-px bg-gray-100" />
          <div className="text-center">
            <p className="text-lg font-semibold text-emerald-600">
              {customer.total_billed.toLocaleString('es-ES', {
                style: 'currency',
                currency: 'EUR',
                maximumFractionDigits: 0,
              })}
            </p>
            <p className="text-xs text-gray-400">Facturado</p>
          </div>
          {customer.pending_amount > 0 && (
            <>
              <div className="h-8 w-px bg-gray-100" />
              <div className="text-center">
                <p className="text-lg font-semibold text-amber-600">
                  {customer.pending_amount.toLocaleString('es-ES', {
                    style: 'currency',
                    currency: 'EUR',
                    maximumFractionDigits: 0,
                  })}
                </p>
                <p className="text-xs text-gray-400">Pendiente</p>
              </div>
            </>
          )}
          {customer.pending_amount > 0 && (
            <span className="ml-auto text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
              Tiene deuda pendiente
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="mt-3 flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-brand-50 text-brand-700 font-medium'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-5">
        {activeTab === 'timeline' && <CustomerTimeline customerId={customer.id} />}

        {activeTab === 'ficha' && (
          editingFicha ? (
            <CustomerForm
              initial={customer}
              onSubmit={(data) => {
                const payload: CustomerUpdatePayload & { id: string } = {
                  id: customer.id,
                  ...data,
                }
                updateCustomer.mutate(payload, { onSuccess: () => setEditingFicha(false) })
              }}
              onCancel={() => setEditingFicha(false)}
              isLoading={updateCustomer.isPending}
            />
          ) : (
            <CustomerFichaView customer={customer} onEdit={() => setEditingFicha(true)} />
          )
        )}

        {activeTab === 'direcciones' && (
          <CustomerAddressList customerId={customer.id} addresses={customer.addresses} />
        )}

        {activeTab === 'documentos' && (
          <CustomerDocumentList customerId={customer.id} documents={customer.documents} />
        )}
      </div>
    </div>
  )
}

function CustomerFichaView({
  customer,
  onEdit,
}: {
  customer: NonNullable<ReturnType<typeof useCustomer>['data']>
  onEdit: () => void
}) {
  const rows: Array<{ label: string; value: string | null }> = [
    { label: 'NIF / CIF', value: customer.tax_id },
    { label: 'Email', value: customer.email },
    { label: 'Teléfono', value: customer.phone },
    { label: 'Teléfono secundario', value: customer.phone_secondary },
    { label: 'Persona de contacto', value: customer.contact_person },
    { label: 'Notas', value: customer.notes },
  ]

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {rows
          .filter((r) => r.value)
          .map((row) => (
            <div key={row.label} className="flex gap-3">
              <span className="text-xs font-medium text-gray-400 w-36 shrink-0 pt-0.5">
                {row.label}
              </span>
              <span className="text-sm text-gray-900">{row.value}</span>
            </div>
          ))}
        {rows.every((r) => !r.value) && (
          <p className="text-sm text-gray-400">No hay datos de contacto registrados.</p>
        )}
      </div>
      <button
        onClick={onEdit}
        className="flex items-center gap-1.5 text-sm text-brand-600 font-medium hover:text-brand-700 transition-colors"
      >
        <Pencil size={14} />
        Editar datos
      </button>
    </div>
  )
}
