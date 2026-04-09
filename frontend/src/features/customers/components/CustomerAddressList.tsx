import { useState } from 'react'
import { Star, Pencil, Trash2, Plus } from 'lucide-react'
import { useAddAddress, useUpdateAddress, useDeleteAddress, useSetDefaultAddress } from '../hooks/use-customers'
import { CustomerAddressForm } from './CustomerAddressForm'
import type { CustomerAddress } from '../types'

interface CustomerAddressListProps {
  customerId: string
  addresses: CustomerAddress[]
}

export function CustomerAddressList({ customerId, addresses }: CustomerAddressListProps) {
  const [showAdd, setShowAdd] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const addAddress = useAddAddress(customerId)
  const updateAddress = useUpdateAddress(customerId)
  const deleteAddress = useDeleteAddress(customerId)
  const setDefault = useSetDefaultAddress(customerId)

  const addressTypeLabel = (type: string) =>
    type === 'fiscal' ? 'Fiscal' : 'Servicio'

  const addressTypeIcon = (type: string) =>
    type === 'fiscal' ? '🏢' : '🔧'

  return (
    <div className="space-y-3">
      {addresses.map((addr) => (
        <div
          key={addr.id}
          className={`border rounded-lg p-3 ${addr.is_default ? 'border-brand-300 bg-brand-50' : 'border-gray-200 bg-white'}`}
        >
          {editingId === addr.id ? (
            <CustomerAddressForm
              initial={addr}
              onSubmit={(data) =>
                updateAddress.mutate(
                  { addressId: addr.id, ...data },
                  { onSuccess: () => setEditingId(null) },
                )
              }
              onCancel={() => setEditingId(null)}
              isLoading={updateAddress.isPending}
            />
          ) : (
            <div className="flex items-start justify-between gap-2">
              <div className="flex gap-2">
                <span className="text-base">{addressTypeIcon(addr.address_type)}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {addressTypeLabel(addr.address_type)}
                    </span>
                    {addr.label && (
                      <span className="text-xs text-gray-400">— {addr.label}</span>
                    )}
                    {addr.is_default && (
                      <span className="flex items-center gap-0.5 text-xs text-brand-600 font-medium">
                        <Star size={10} className="fill-current" />
                        Predeterminada
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-900 mt-0.5">{addr.street}</p>
                  <p className="text-sm text-gray-600">
                    {addr.postal_code} {addr.city}
                    {addr.province ? `, ${addr.province}` : ''}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {!addr.is_default && (
                  <button
                    onClick={() => setDefault.mutate(addr.id)}
                    title="Marcar como predeterminada"
                    className="p-1.5 text-gray-400 hover:text-amber-500 transition-colors"
                  >
                    <Star size={14} />
                  </button>
                )}
                <button
                  onClick={() => setEditingId(addr.id)}
                  title="Editar"
                  className="p-1.5 text-gray-400 hover:text-gray-700 transition-colors"
                >
                  <Pencil size={14} />
                </button>
                {addresses.length > 1 && (
                  <button
                    onClick={() => {
                      if (confirm('¿Eliminar esta dirección?')) deleteAddress.mutate(addr.id)
                    }}
                    title="Eliminar"
                    className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      {showAdd ? (
        <div className="border border-dashed border-gray-300 rounded-lg p-3">
          <CustomerAddressForm
            onSubmit={(data) =>
              addAddress.mutate(data, { onSuccess: () => setShowAdd(false) })
            }
            onCancel={() => setShowAdd(false)}
            isLoading={addAddress.isPending}
          />
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
        >
          <Plus size={14} />
          Añadir dirección
        </button>
      )}
    </div>
  )
}
