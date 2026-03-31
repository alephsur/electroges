import { useState } from 'react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useCustomers } from '@/features/customers/hooks/use-customers'
import { useCreateWorkOrder } from '../hooks/use-work-orders'

interface NewWorkOrderModalProps {
  onClose: () => void
  onCreated: (workOrderId: string) => void
}

export function NewWorkOrderModal({ onClose, onCreated }: NewWorkOrderModalProps) {
  const [customerId, setCustomerId] = useState('')
  const [customerSearch, setCustomerSearch] = useState('')
  const [address, setAddress] = useState('')
  const [notes, setNotes] = useState('')

  const { data: customersData } = useCustomers({
    q: customerSearch || undefined,
    limit: 50,
  })
  const customers = customersData?.items ?? []

  const createWorkOrder = useCreateWorkOrder()

  const handleSubmit = async () => {
    if (!customerId) return
    try {
      const workOrder = await createWorkOrder.mutateAsync({
        customer_id: customerId,
        address: address.trim() || undefined,
        notes: notes.trim() || undefined,
      })
      onCreated(workOrder.id)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Nueva obra</h2>
        </div>

        <div className="space-y-4 px-6 py-4">
          {/* Customer search */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Cliente <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="Buscar cliente…"
              value={customerSearch}
              onChange={(e) => {
                setCustomerSearch(e.target.value)
                setCustomerId('')
              }}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
              autoFocus
            />
            {customers.length > 0 && !customerId && (
              <div className="mt-1 max-h-40 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-sm">
                {customers.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      setCustomerId(c.id)
                      setCustomerSearch(c.name)
                    }}
                    className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Dirección de la obra
            </label>
            <input
              type="text"
              placeholder="Dirección (opcional)"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Notas
            </label>
            <textarea
              placeholder="Notas iniciales (opcional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!customerId || createWorkOrder.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createWorkOrder.isPending ? 'Creando…' : 'Crear obra'}
          </button>
        </div>
      </div>
    </div>
  )
}
