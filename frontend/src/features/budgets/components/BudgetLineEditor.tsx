import { Fragment, useMemo, useState } from 'react'
import {
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Package,
  FolderPlus,
  ChevronDown,
  ChevronRight,
  FolderOpen,
} from 'lucide-react'
import type {
  Budget,
  BudgetLine,
  BudgetLineCreatePayload,
  BudgetLineType,
  BudgetSection,
} from '../types'
import type { InventoryItem } from '@/features/inventory/types'
import {
  useAddLine,
  useDeleteLine,
  useUpdateLine,
} from '../hooks/use-budget-lines'
import {
  useAssignLineToSection,
  useCreateSection,
  useDeleteSection,
  useUpdateSection,
} from '../hooks/use-budget-sections'
import { useBudgetStore } from '../store/budget-store'
import { InventoryItemPicker } from '@/shared/components/InventoryItemPicker'

interface BudgetLineEditorProps {
  budget: Budget
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
      <td className="px-3 py-2" colSpan={8}>
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
  sectionId: string | null
  onClose: () => void
}

function AddLineForm({ budgetId, sectionId, onClose }: AddLineFormProps) {
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
      section_id: sectionId,
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
    <tr className="bg-green-50 border-t border-green-100">
      <td className="px-3 py-2" colSpan={8}>
        <div className="space-y-2">
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
                <label className="block text-xs text-gray-500 mb-0.5">
                  Material del inventario
                </label>
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
  )
}

// ── Section header (rename / delete inline) ───────────────────────────────────

interface SectionHeaderProps {
  section: BudgetSection
  budgetId: string
  collapsed: boolean
  onToggle: () => void
  readOnly: boolean
  otherSections: BudgetSection[]
  sectionLines: BudgetLine[]
  onAddLine: () => void
}

function SectionHeader({
  section,
  budgetId,
  collapsed,
  onToggle,
  readOnly,
  otherSections,
  sectionLines,
  onAddLine,
}: SectionHeaderProps) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(section.name)
  const [notes, setNotes] = useState(section.notes ?? '')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [reassignTo, setReassignTo] = useState<string | 'none'>('none')
  const updateSection = useUpdateSection(budgetId)
  const deleteSection = useDeleteSection(budgetId)
  const assignLine = useAssignLineToSection(budgetId)
  const hasLines = sectionLines.length > 0

  const handleSave = () => {
    updateSection.mutate(
      { sectionId: section.id, name, notes: notes || null },
      { onSuccess: () => setEditing(false) },
    )
  }

  const handleDelete = async () => {
    // Move lines to another section first if requested
    // (if reassignTo === 'none', backend ON DELETE SET NULL handles it)
    if (hasLines && reassignTo !== 'none') {
      await Promise.all(
        sectionLines.map((line) =>
          assignLine.mutateAsync({ lineId: line.id, sectionId: reassignTo }),
        ),
      )
    }
    deleteSection.mutate(section.id, {
      onSuccess: () => setConfirmDelete(false),
    })
  }

  if (editing) {
    return (
      <tr className="bg-indigo-50 border-y border-indigo-200">
        <td colSpan={8} className="px-3 py-2">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="block text-xs text-indigo-700 mb-0.5">
                Nombre del capítulo
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                autoFocus
              />
            </div>
            <div className="flex-[2]">
              <label className="block text-xs text-indigo-700 mb-0.5">
                Notas (opcional)
              </label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <button
              onClick={handleSave}
              disabled={!name.trim() || updateSection.isPending}
              className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              <Check size={13} />
            </button>
            <button
              onClick={() => {
                setName(section.name)
                setNotes(section.notes ?? '')
                setEditing(false)
              }}
              className="rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
            >
              <X size={13} />
            </button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <>
      <tr className="bg-indigo-50 border-y border-indigo-100 group">
        <td colSpan={8} className="px-3 py-2">
          <div className="flex items-center gap-2">
            <button
              onClick={onToggle}
              className="text-indigo-700 hover:text-indigo-900"
            >
              {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
            </button>
            <FolderOpen size={14} className="text-indigo-700" />
            <span className="font-semibold text-indigo-900 text-sm">
              {section.name}
            </span>
            {section.notes && (
              <span className="text-xs text-indigo-600 truncate max-w-xs">
                · {section.notes}
              </span>
            )}
            <span className="ml-auto text-xs font-medium text-indigo-800">
              {formatEur(section.subtotal)} €
            </span>
            {!readOnly && (
              <div className="flex items-center gap-1">
                <button
                  onClick={onAddLine}
                  title="Añadir línea al capítulo"
                  className="rounded p-1 text-indigo-600 hover:bg-indigo-100"
                >
                  <Plus size={13} />
                </button>
                <button
                  onClick={() => setEditing(true)}
                  title="Renombrar"
                  className="rounded p-1 text-indigo-600 hover:bg-indigo-100"
                >
                  <Edit2 size={13} />
                </button>
                <button
                  onClick={() => setConfirmDelete(true)}
                  title="Eliminar capítulo"
                  className="rounded p-1 text-red-500 hover:bg-red-50"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            )}
          </div>
        </td>
      </tr>

      {confirmDelete && !readOnly && (
        <tr className="bg-red-50 border-b border-red-200">
          <td colSpan={8} className="px-3 py-2">
            <div className="space-y-2">
              <div className="text-sm text-red-800">
                ¿Eliminar el capítulo <strong>{section.name}</strong>?
              </div>
              {hasLines && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-red-700">Mover sus líneas a:</span>
                  <select
                    value={reassignTo}
                    onChange={(e) => setReassignTo(e.target.value)}
                    className="rounded border border-gray-300 px-2 py-1 text-sm"
                  >
                    <option value="none">Sin capítulo</option>
                    {otherSections.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={handleDelete}
                  disabled={deleteSection.isPending}
                  className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Eliminar
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Line row ──────────────────────────────────────────────────────────────────

interface LineRowProps {
  line: BudgetLine
  budgetId: string
  sections: BudgetSection[]
  readOnly: boolean
}

function LineRow({ line, budgetId, sections, readOnly }: LineRowProps) {
  const deleteLine = useDeleteLine(budgetId)
  const assignToSection = useAssignLineToSection(budgetId)
  const { editingLineId, setEditingLineId } = useBudgetStore()

  if (editingLineId === line.id && !readOnly) {
    return (
      <InlineEditForm
        line={line}
        budgetId={budgetId}
        onClose={() => setEditingLineId(null)}
      />
    )
  }

  return (
    <tr className="hover:bg-gray-50">
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
            {sections.length > 0 && (
              <select
                value={line.section_id ?? ''}
                onChange={(e) =>
                  assignToSection.mutate({
                    lineId: line.id,
                    sectionId: e.target.value || null,
                  })
                }
                title="Mover a capítulo"
                className="rounded border border-gray-200 bg-white text-xs px-1 py-0.5 text-gray-500 hover:border-indigo-300"
              >
                <option value="">Sin capítulo</option>
                {sections.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
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
  )
}

// ── New section inline form ───────────────────────────────────────────────────

function NewSectionForm({
  budgetId,
  onClose,
}: {
  budgetId: string
  onClose: () => void
}) {
  const createSection = useCreateSection(budgetId)
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')

  const handleCreate = () => {
    if (!name.trim()) return
    createSection.mutate(
      { name: name.trim(), notes: notes.trim() || null },
      { onSuccess: onClose },
    )
  }

  return (
    <div className="rounded-md border-2 border-dashed border-indigo-300 bg-indigo-50 p-3 mt-3">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="block text-xs text-indigo-700 mb-0.5">
            Nombre del capítulo
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Cuadro eléctrico"
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
            autoFocus
          />
        </div>
        <div className="flex-[2]">
          <label className="block text-xs text-indigo-700 mb-0.5">
            Notas (opcional)
          </label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Descripción breve"
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <button
          onClick={handleCreate}
          disabled={!name.trim() || createSection.isPending}
          className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Crear
        </button>
        <button
          onClick={onClose}
          className="rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}

// ── Main editor ───────────────────────────────────────────────────────────────

export function BudgetLineEditor({ budget, readOnly = false }: BudgetLineEditorProps) {
  const { showAddLineForm, setShowAddLineForm } = useBudgetStore()
  const [addingToSection, setAddingToSection] = useState<string | null | '__new__'>(null)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [showNewSection, setShowNewSection] = useState(false)

  const sectionsSorted = useMemo(
    () => [...budget.sections].sort((a, b) => a.sort_order - b.sort_order),
    [budget.sections],
  )

  const linesBySection = useMemo(() => {
    const map = new Map<string | null, BudgetLine[]>()
    for (const line of budget.lines) {
      const key = line.section_id ?? null
      const arr = map.get(key) ?? []
      arr.push(line)
      map.set(key, arr)
    }
    for (const [k, arr] of map.entries()) {
      arr.sort((a, b) => a.sort_order - b.sort_order)
      map.set(k, arr)
    }
    return map
  }, [budget.lines])

  const unsectionedLines = linesBySection.get(null) ?? []

  const handleAddLineClick = (sectionId: string | null) => {
    setAddingToSection(sectionId)
    setShowAddLineForm(true)
  }

  const closeAddLine = () => {
    setShowAddLineForm(false)
    setAddingToSection(null)
  }

  const renderHeader = () => (
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
  )

  return (
    <div>
      {/* Top action bar with section controls */}
      {!readOnly && (
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs text-gray-500">
            {sectionsSorted.length > 0
              ? `${sectionsSorted.length} ${sectionsSorted.length === 1 ? 'capítulo' : 'capítulos'} · ${budget.lines.length} líneas`
              : `${budget.lines.length} líneas (sin capítulos)`}
          </div>
          <button
            onClick={() => setShowNewSection(true)}
            className="flex items-center gap-1.5 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
          >
            <FolderPlus size={13} />
            Nuevo capítulo
          </button>
        </div>
      )}

      <table className="w-full text-sm">
        {renderHeader()}
        <tbody className="divide-y divide-gray-100">
          {/* Sections */}
          {sectionsSorted.map((section) => {
            const sectionLines = linesBySection.get(section.id) ?? []
            const isCollapsed = collapsed[section.id]
            const others = sectionsSorted.filter((s) => s.id !== section.id)
            return (
              <Fragment key={section.id}>
                <SectionHeader
                  section={section}
                  budgetId={budget.id}
                  collapsed={!!isCollapsed}
                  onToggle={() =>
                    setCollapsed((prev) => ({
                      ...prev,
                      [section.id]: !prev[section.id],
                    }))
                  }
                  readOnly={readOnly}
                  otherSections={others}
                  sectionLines={sectionLines}
                  onAddLine={() => handleAddLineClick(section.id)}
                />
                {!isCollapsed &&
                  sectionLines.map((line) => (
                    <LineRow
                      key={line.id}
                      line={line}
                      budgetId={budget.id}
                      sections={sectionsSorted}
                      readOnly={readOnly}
                    />
                  ))}
                {!isCollapsed &&
                  showAddLineForm &&
                  addingToSection === section.id && (
                    <AddLineForm
                      budgetId={budget.id}
                      sectionId={section.id}
                      onClose={closeAddLine}
                    />
                  )}
              </Fragment>
            )
          })}

          {/* Unsectioned bucket */}
          {(unsectionedLines.length > 0 || sectionsSorted.length === 0) && (
            <Fragment>
              {sectionsSorted.length > 0 && unsectionedLines.length > 0 && (
                <tr className="bg-gray-50 border-y border-gray-200">
                  <td colSpan={8} className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                        Sin capítulo
                      </span>
                      {!readOnly && (
                        <button
                          onClick={() => handleAddLineClick(null)}
                          title="Añadir línea sin capítulo"
                          className="rounded p-1 text-gray-500 hover:bg-gray-200"
                        >
                          <Plus size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
              {unsectionedLines.map((line) => (
                <LineRow
                  key={line.id}
                  line={line}
                  budgetId={budget.id}
                  sections={sectionsSorted}
                  readOnly={readOnly}
                />
              ))}
              {showAddLineForm && addingToSection === null && (
                <AddLineForm
                  budgetId={budget.id}
                  sectionId={null}
                  onClose={closeAddLine}
                />
              )}
            </Fragment>
          )}
        </tbody>
      </table>

      {!readOnly && showNewSection && (
        <NewSectionForm
          budgetId={budget.id}
          onClose={() => setShowNewSection(false)}
        />
      )}

      {!readOnly && !showAddLineForm && (
        <button
          onClick={() => handleAddLineClick(null)}
          className="mt-2 flex items-center gap-1.5 rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 w-full justify-center"
        >
          <Plus size={14} />
          Añadir línea {sectionsSorted.length > 0 ? '(sin capítulo)' : ''}
        </button>
      )}
    </div>
  )
}
