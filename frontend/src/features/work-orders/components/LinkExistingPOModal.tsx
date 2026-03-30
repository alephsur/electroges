import { useState } from 'react'
import { X } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useSuppliers } from '@/features/suppliers/hooks/use-suppliers'
import { usePurchaseOrders } from '@/features/suppliers/hooks/use-purchase-orders'
import { useLinkPurchaseOrder } from '../hooks/use-work-order-purchase-orders'

function fmt(n: number | string) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const PO_STATUS: Record<string, { label: string; className: string }> = {
  pending:   { label: 'Pendiente',  className: 'bg-amber-100 text-amber-700' },
  received:  { label: 'Recibido',   className: 'bg-green-100 text-green-700' },
  cancelled: { label: 'Cancelado',  className: 'bg-gray-100 text-gray-500' },
}

interface LinkExistingPOModalProps {
  workOrderId: string
  alreadyLinkedIds: string[]
  onClose: () => void
}

export function LinkExistingPOModal({
  workOrderId,
  alreadyLinkedIds,
  onClose,
}: LinkExistingPOModalProps) {
  const [supplierSearch, setSupplierSearch] = useState('')
  const [selectedSupplierId, setSelectedSupplierId] = useState('')
  const [selectedSupplierName, setSelectedSupplierName] = useState('')
  const [supplierFocused, setSupplierFocused] = useState(false)

  const { data: suppliersData } = useSuppliers({ q: supplierSearch || undefined, limit: 20 })
  const suppliers = suppliersData?.items ?? []
  const showSupplierDropdown =
    supplierFocused && suppliers.length > 0 && !selectedSupplierId

  const { data: posData } = usePurchaseOrders(selectedSupplierId || null, { limit: 100 })
  const allPOs = posData?.items ?? []
  // Exclude already-linked POs
  const availablePOs = allPOs.filter((po) => !alreadyLinkedIds.includes(po.id))

  const link = useLinkPurchaseOrder()

  const handleLink = async (purchaseOrderId: string) => {
    try {
      await link.mutateAsync({ workOrderId, purchase_order_id: purchaseOrderId })
      onClose()
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-20">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Vincular pedido existente</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {/* Supplier search */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
            <input
              type="text"
              placeholder="Buscar proveedor…"
              value={supplierSearch}
              onChange={(e) => {
                setSupplierSearch(e.target.value)
                setSelectedSupplierId('')
                setSelectedSupplierName('')
              }}
              onFocus={() => setSupplierFocused(true)}
              onBlur={() => setTimeout(() => setSupplierFocused(false), 150)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
              autoFocus
            />
            {showSupplierDropdown && (
              <div className="absolute z-30 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
                {suppliers.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setSelectedSupplierId(s.id)
                      setSelectedSupplierName(s.name)
                      setSupplierSearch(s.name)
                    }}
                    className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* PO list */}
          {selectedSupplierId && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Pedidos de {selectedSupplierName}
              </p>
              {availablePOs.length === 0 ? (
                <p className="py-4 text-center text-sm text-gray-400">
                  No hay pedidos disponibles para vincular.
                </p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {availablePOs.map((po) => {
                    const cfg = PO_STATUS[po.status] ?? { label: po.status, className: 'bg-gray-100 text-gray-600' }
                    return (
                      <div
                        key={po.id}
                        className="flex items-center justify-between rounded-lg border border-gray-100 p-3 hover:border-blue-200 hover:bg-blue-50"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">{po.order_number}</span>
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}>
                              {cfg.label}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {String(po.order_date)} · {fmt(po.total)} €
                          </p>
                        </div>
                        <button
                          onClick={() => handleLink(po.id)}
                          disabled={link.isPending}
                          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                          Vincular
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
