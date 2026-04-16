import { useState } from 'react'
import { Plus, Trash2, Edit2, Check, X, Package } from 'lucide-react'
import type { BudgetLine, BudgetLineCreatePayload, BudgetLineType } from '../types'
import type { InventoryItem } from '@/features/inventory/types'
import { useAddLine, useDeleteLine, useUpdateLine } from '../hooks/use-budget-lines'
import { useBudgetStore } from '../store/budget-store'
import { InventoryItemPicker } from '@/shared/components/InventoryItemPicker'

interface BudgetLineEditorProps {
  budgetId: string
  lines: BudgetLine[]
  readOnly?: boolean
}

const LINE_TYPE_LABELS: Record<BudgetLineType, string> = {
  labor: 'Mano de obra',
  material: 'Material',
  other: 'Partida',
}

const LINE_TYPE_CLASSES: Record<BudgetLineType, string> = {
  labor: 'bg-blue-100 text-blue-700',
  material: 'bg-green-100 text-green-700',
  other: 'bg-gray-100 text-gray-600',
}

function formatEur(value: number) {
  return Number(value).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

// ── Inline edit form ──────────────────────────────────────────────────────────

interface InlineEditFormProps {
  line: BudgetLine
  budgetId: string
  onClose: () => void
}

function InlineEditForm({ line, budgetId, onClose }: InlineEditFormProps) {
  const updateLine = useUpdateLine(budgetId)
  const [description, setDescription] = useState(line.description)
  const [quantity, setQuantity] = useState(String(line.quantity))
  const [unitPrice, setUnitPrice] = useState(String(line.unit_price))
  const [unitCost, setUnitCost] = useState(String(line.unit_cost))
  const [unit, setUnit] = useState(line.unit ?? '')
  const [lineDiscount, setLineDiscount] = useState(String(line.line_discount_pct))

  const handleSave = () => {
    updateLine.mutate(
      {
        lineId: line.id,
        description,
        quantity: parseFloat(quantity),
        unit_price: parseFloat(unitPrice),
        unit_cost: parseFloat(unitCost),
        unit: unit || null,
        line_discount_pct: parseFloat(lineDiscount),
      },
      { onSuccess: onClose },
    )
  }

  return (
    <tr className="bg-blue-50">
      <td className="px-3 py-2" colSpan={7}>
        <div className="grid grid-cols-6 gap-2">
          <div className="col-span-2">
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descripción"
              className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <input
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            type="number"
            step="0.001"
            placeholder="Cant."
            className="rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            placeholder="Ud."
            className="rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            value={unitPrice}
            onChange={(e) => setUnitPrice(e.target.value)}
            type="number"
            step="0.0001"
            placeholder="P.unit."
            className="rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            value={unitCost}
            onChange={(e) => setUnitCost(e.target.value)}
            type="number"
            step="0.0001"
            placeholder="Coste"
            className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400"
          />
        </div>
        <div className="mt-1 flex gap-1 justify-end">
          <input
            value={lineDiscount}
            onChange={(e) => setLineDiscount(e.target.value)}
            type="number"
            step="0.01"
            min="0"
            max="100"
            placeholder="Dto. línea %"
            className="w-28 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleSave}
            disabled={updateLine.isPending}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Check size={13} />
          </button>
          <button
            onClick={onClose}
            className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            <X size={13} />
          </button>
        </div>
      </td>
    </tr>
  )
}

// ── Add line form ─────────────────────────────────────────────────────────────

interface AddLineFormProps {
  budgetId: string
  onClose: () => void
}

function AddLineForm({ budgetId, onClose }: AddLineFormProps) {
  const addLine = useAddLine(budgetId)
  const [lineType, setLineType] = useState<BudgetLineType>('labor')
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [unit, setUnit] = useState('')
  const [unitPrice, setUnitPrice] = useState('0')
  const [unitCost, setUnitCost] = useState('0')
  const [lineDiscount, setLineDiscount] = useState('0')
  const [inventoryItemId, setInventoryItemId] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null)

  const isMaterial = lineType === 'material'

  const handleItemChange = (item: InventoryItem | null) => {
    setSelectedItem(item)
    setInventoryItemId(item?.id ?? null)
    if (item) {
      setDescription(item.name)
      setUnit(item.unit)
      setUnitPrice(String(item.unit_price))
      setUnitCost(String(Number(item.unit_cost_avg || 0)))
    } else {
      setDescription('')
      setUnit('')
      setUnitPrice('0')
      setUnitCost('0')
    }
  }

  const handleTypeChange = (newType: BudgetLineType) => {
    setLineType(newType)
    if (newType !== 'material' && inventoryItemId) {
      handleItemChange(null)
    }
  }

  const handleAdd = () => {
    const payload: BudgetLineCreatePayload = {
      line_type: lineType,
      description,
      inventory_item_id: isMaterial ? inventoryItemId : undefined,
      quantity: parseFloat(quantity),
      unit: unit || null,
      unit_price: parseFloat(unitPrice),
      unit_cost: parseFloat(unitCost),
      line_discount_pct: parseFloat(lineDiscount),
    }
    addLine.mutate(payload, {
      onSuccess: () => {
        setDescription('')
        setQuantity('1')
        setUnit('')
        setUnitPrice('0')
        setUnitCost('0')
        setInventoryItemId(null)
        onClose()
      },
    })
  }

  return (
    <>
      <tr className="bg-green-50 border-t border-green-100">
        <td className="px-3 py-2" colSpan={7}>
          <div className="space-y-2">
            {/* Row 1: type + description/material selector */}
            <div className="flex items-end gap-2">
              <div className="w-32 shrink-0">
                <label className="block text-xs text-gray-500 mb-0.5">Tipo</label>
                <select
                  value={lineType}
                  onChange={(e) => handleTypeChange(e.target.value as BudgetLineType)}
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="labor">Mano de obra</option>
                  <option value="material">Material</option>
                  <option value="other">Otro</option>
                </select>
              </div>

              {isMaterial ? (
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-0.5">Material del inventario</label>
                  <InventoryItemPicker
                    value={selectedItem}
                    onChange={handleItemChange}
                    placeholder="Buscar o crear material…"
                  />
                </div>
              ) : (
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-0.5">Descripción</label>
                  <input
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Descripción de la línea"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>

            {/* Row 2: numeric fields */}
            <div className="grid grid-cols-5 gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">Cant.</label>
                <input
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  type="number"
                  step="0.001"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">Ud.</label>
                <input
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="uds"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  readOnly={isMaterial && !!inventoryItemId}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">P. venta</label>
                <input
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(e.target.value)}
                  type="number"
                  step="0.01"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">Dto. %</label>
                <input
                  value={lineDiscount}
                  onChange={(e) => setLineDiscount(e.target.value)}
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-amber-600 mb-0.5">Coste</label>
                <input
                  value={unitCost}
                  onChange={(e) => setUnitCost(e.target.value)}
                  type="number"
                  step="0.01"
                  className="w-full rounded border border-amber-200 bg-amber-50 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400"
                />
              </div>
            </div>

            {/* Row 3: actions */}
            <div className="flex justify-end gap-1">
              <button
                onClick={handleAdd}
                disabled={(!description && !inventoryItemId) || addLine.isPending}
                className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {addLine.isPending ? '...' : 'Añadir'}
              </button>
              <button
                onClick={onClose}
                className="rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
              >
                <X size={13} />
              </button>
            </div>
          </div>
        </td>
      </tr>

    </>
  )
}

// ── Main editor ───────────────────────────────────────────────────────────────

export function BudgetLineEditor({ budgetId, lines, readOnly = false }: BudgetLineEditorProps) {
  const deleteLine = useDeleteLine(budgetId)
  const { editingLineId, setEditingLineId, showAddLineForm, setShowAddLineForm } = useBudgetStore()

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-xs text-gray-500">
            <th className="pb-2 text-left font-medium px-3">Tipo</th>
            <th className="pb-2 text-left font-medium px-3">Descripción</th>
            <th className="pb-2 text-right font-medium px-3">Cant.</th>
            <th className="pb-2 text-right font-medium px-3">Ud.</th>
            <th className="pb-2 text-right font-medium px-3">P.unit.</th>
            <th className="pb-2 text-right font-medium px-3">Margen</th>
            <th className="pb-2 text-right font-medium px-3">Subtotal</th>
            {!readOnly && <th className="pb-2 px-3" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {lines.map((line) =>
            editingLineId === line.id && !readOnly ? (
              <InlineEditForm
                key={line.id}
                line={line}
                budgetId={budgetId}
                onClose={() => setEditingLineId(null)}
              />
            ) : (
              <tr key={line.id} className="hover:bg-gray-50">
                <td className="py-2 px-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      LINE_TYPE_CLASSES[line.line_type as BudgetLineType]
                    }`}
                  >
                    {LINE_TYPE_LABELS[line.line_type as BudgetLineType]}
                  </span>
                </td>
                <td className="py-2 px-3 text-gray-800">
                  <div>{line.description}</div>
                  {line.inventory_item_name && (
                    <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                      <Package size={10} />
                      {line.inventory_item_name}
                    </div>
                  )}
                </td>
                <td className="py-2 px-3 text-right text-gray-600">{line.quantity}</td>
                <td className="py-2 px-3 text-right text-gray-500">{line.unit ?? ''}</td>
                <td className="py-2 px-3 text-right text-gray-600">
                  {formatEur(line.unit_price)}
                </td>
                <td className="py-2 px-3 text-right">
                  <span
                    className={`text-xs font-medium ${
                      Number(line.margin_pct) < 15
                        ? 'text-red-600'
                        : Number(line.margin_pct) < 25
                          ? 'text-amber-600'
                          : 'text-green-600'
                    }`}
                  >
                    {Number(line.margin_pct).toFixed(1)}%
                  </span>
                </td>
                <td className="py-2 px-3 text-right font-medium text-gray-900">
                  {formatEur(line.subtotal)} €
                </td>
                {!readOnly && (
                  <td className="py-2 px-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditingLineId(line.id)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        onClick={() => deleteLine.mutate(line.id)}
                        disabled={deleteLine.isPending}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ),
          )}
          {!readOnly && showAddLineForm && (
            <AddLineForm budgetId={budgetId} onClose={() => setShowAddLineForm(false)} />
          )}
        </tbody>
      </table>

      {!readOnly && !showAddLineForm && (
        <button
          onClick={() => setShowAddLineForm(true)}
          className="mt-2 flex items-center gap-1.5 rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 w-full justify-center"
        >
          <Plus size={14} />
          Añadir línea
        </button>
      )}
    </div>
  )
}
