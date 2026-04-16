import { useState } from 'react'
import { Plus, Trash2, X } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useSuppliers } from '@/features/suppliers/hooks/use-suppliers'
import { useSupplierInventoryItems } from '@/features/suppliers/hooks/use-supplier-inventory'
import { useCreateAndLinkPurchaseOrder } from '../hooks/use-work-order-purchase-orders'

function fmt(n: number) {
  return n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── Line row ──────────────────────────────────────────────────────────────────

interface LineState {
  key: string
  itemSearch: string
  selectedItemId: string
  description: string
  qty: string
  unitCost: string
}

function newLine(): LineState {
  return {
    key: crypto.randomUUID(),
    itemSearch: '',
    selectedItemId: '',
    description: '',
    qty: '',
    unitCost: '',
  }
}

interface SupplierItem {
  id: string
  name: string
  unit: string
  unit_cost: string
  unit_cost_avg?: string
}

interface LineRowProps {
  line: LineState
  supplierItems: SupplierItem[]
  onChange: (updated: LineState) => void
  onRemove: () => void
}

function LineRow({ line, supplierItems, onChange, onRemove }: LineRowProps) {
  const [focused, setFocused] = useState(false)

  // Filter supplier items by search text (client-side, supplier items are few)
  const filtered = line.itemSearch.trim()
    ? supplierItems.filter((item) =>
        item.name.toLowerCase().includes(line.itemSearch.toLowerCase()),
      )
    : supplierItems

  const showDropdown = focused && filtered.length > 0 && !line.selectedItemId

  const qty = parseFloat(line.qty.replace(',', '.'))
  const cost = parseFloat(line.unitCost.replace(',', '.'))
  const subtotal = !isNaN(qty) && !isNaN(cost) ? qty * cost : null

  return (
    <div className="grid grid-cols-[1fr_auto_auto_auto] items-start gap-2 rounded-lg border border-gray-100 bg-gray-50 p-3">
      {/* Item / description */}
      <div className="relative">
        <input
          type="text"
          placeholder={
            supplierItems.length > 0
              ? 'Buscar artículo del proveedor…'
              : 'Descripción libre…'
          }
          value={line.itemSearch}
          onChange={(e) =>
            onChange({
              ...line,
              itemSearch: e.target.value,
              selectedItemId: '',
              description: e.target.value,
            })
          }
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
        />
        {showDropdown && (
          <div className="absolute z-30 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
            {filtered.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() =>
                  onChange({
                    ...line,
                    selectedItemId: item.id,
                    itemSearch: item.name,
                    description: item.name,
                    unitCost: String(Number(item.unit_cost_avg || 0)),
                  })
                }
                className="flex w-full items-baseline justify-between px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                <span className="font-medium">{item.name}</span>
                <span className="ml-3 shrink-0 text-xs text-gray-400">
                  {item.unit} · {fmt(Number(item.unit_cost_avg || 0))} €/ud
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Quantity */}
      <div className="w-24">
        <input
          type="number"
          min="0"
          step="0.001"
          placeholder="Cant."
          value={line.qty}
          onChange={(e) => onChange({ ...line, qty: e.target.value })}
          className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
        />
      </div>

      {/* Unit cost */}
      <div className="w-28">
        <input
          type="number"
          min="0"
          step="0.0001"
          placeholder="€/ud"
          value={line.unitCost}
          onChange={(e) => onChange({ ...line, unitCost: e.target.value })}
          className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
        />
      </div>

      {/* Subtotal + delete */}
      <div className="flex items-center gap-2 pt-1.5">
        <span className="w-20 text-right text-sm text-gray-700">
          {subtotal !== null ? `${fmt(subtotal)} €` : '—'}
        </span>
        <button type="button" onClick={onRemove} className="text-gray-300 hover:text-red-500">
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

// ── Modal ─────────────────────────────────────────────────────────────────────

interface NewPurchaseOrderModalProps {
  workOrderId: string
  onClose: () => void
}

export function NewPurchaseOrderModal({ workOrderId, onClose }: NewPurchaseOrderModalProps) {
  const today = new Date().toISOString().slice(0, 10)

  const [supplierSearch, setSupplierSearch] = useState('')
  const [selectedSupplierId, setSelectedSupplierId] = useState('')
  const [selectedSupplierName, setSelectedSupplierName] = useState('')
  const [orderDate, setOrderDate] = useState(today)
  const [expectedDate, setExpectedDate] = useState('')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<LineState[]>([newLine()])

  const { data: suppliersData } = useSuppliers({ q: supplierSearch || undefined, limit: 20 })
  const suppliers = suppliersData?.items ?? []
  const showSupplierDropdown =
    suppliers.length > 0 && !selectedSupplierId && supplierSearch.length > 0

  // Load all items for selected supplier (client-side filtering in each LineRow)
  const { data: supplierItemsData } = useSupplierInventoryItems(
    selectedSupplierId || null,
    { limit: 200 },
  )
  const supplierItems = supplierItemsData?.items ?? []

  const create = useCreateAndLinkPurchaseOrder()

  const updateLine = (key: string, updated: LineState) =>
    setLines((prev) => prev.map((l) => (l.key === key ? updated : l)))

  const removeLine = (key: string) =>
    setLines((prev) => prev.filter((l) => l.key !== key))

  const total = lines.reduce((acc, l) => {
    const qty = parseFloat(l.qty.replace(',', '.'))
    const cost = parseFloat(l.unitCost.replace(',', '.'))
    return acc + (!isNaN(qty) && !isNaN(cost) ? qty * cost : 0)
  }, 0)

  const canSubmit =
    selectedSupplierId &&
    orderDate &&
    lines.length > 0 &&
    lines.every((l) => {
      const qty = parseFloat(l.qty.replace(',', '.'))
      const cost = parseFloat(l.unitCost.replace(',', '.'))
      return (
        (l.selectedItemId || l.description.trim()) &&
        !isNaN(qty) &&
        qty > 0 &&
        !isNaN(cost)
      )
    })

  const handleSubmit = async () => {
    if (!canSubmit) return
    try {
      await create.mutateAsync({
        workOrderId,
        supplier_id: selectedSupplierId,
        order_date: orderDate,
        expected_date: expectedDate || null,
        notes: notes.trim() || null,
        lines: lines.map((l) => ({
          inventory_item_id: l.selectedItemId || null,
          description: l.selectedItemId ? null : l.description.trim() || null,
          quantity: parseFloat(l.qty.replace(',', '.')),
          unit_cost: parseFloat(l.unitCost.replace(',', '.')),
        })),
      })
      onClose()
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-12">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Nuevo pedido</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-5 px-6 py-5">
          {/* Supplier */}
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
                // Reset lines when supplier changes
                setLines([newLine()])
              }}
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
                      setLines([newLine()])
                    }}
                    className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <span className="font-medium">{s.name}</span>
                    {s.tax_id && (
                      <span className="ml-2 text-xs text-gray-400">{s.tax_id}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
            {selectedSupplierId && (
              <p className="mt-1 text-xs text-green-600">
                ✓ {selectedSupplierName}
                {supplierItems.length > 0 && (
                  <span className="ml-2 text-gray-400">
                    · {supplierItems.length} artículo{supplierItems.length !== 1 ? 's' : ''} disponible{supplierItems.length !== 1 ? 's' : ''}
                  </span>
                )}
              </p>
            )}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha pedido</label>
              <input
                type="date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha entrega prevista{' '}
                <span className="text-gray-400">(opcional)</span>
              </label>
              <input
                type="date"
                value={expectedDate}
                onChange={(e) => setExpectedDate(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notas <span className="text-gray-400">(opcional)</span>
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Condiciones, referencias, etc."
              className="w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </div>

          {/* Lines */}
          <div>
            <div className="mb-2 grid grid-cols-[1fr_auto_auto_auto] gap-2 px-1">
              <span className="text-xs font-medium text-gray-500">Artículo / descripción</span>
              <span className="w-24 text-right text-xs font-medium text-gray-500">Cantidad</span>
              <span className="w-28 text-right text-xs font-medium text-gray-500">€/ud</span>
              <span className="w-24 text-right text-xs font-medium text-gray-500">Subtotal</span>
            </div>

            <div className="space-y-2">
              {lines.map((line) => (
                <LineRow
                  key={line.key}
                  line={line}
                  supplierItems={supplierItems}
                  onChange={(updated) => updateLine(line.key, updated)}
                  onRemove={() => removeLine(line.key)}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={() => setLines((prev) => [...prev, newLine()])}
              className="mt-2 flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
            >
              <Plus size={14} />
              Añadir línea
            </button>
          </div>

          {/* Total */}
          <div className="flex justify-end border-t border-gray-100 pt-3">
            <span className="text-sm font-semibold text-gray-900">
              Total: {fmt(total)} €
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || create.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {create.isPending ? 'Creando…' : 'Crear pedido'}
          </button>
        </div>
      </div>
    </div>
  )
}
