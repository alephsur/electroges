import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useInventoryItems } from '@/features/inventory/hooks/use-inventory-items'
import { useAddMaterial, useConsumeMaterial, useRemoveMaterial } from '../hooks/use-work-order-tasks'
import type { Task, TaskMaterial } from '../types'

function fmtQty(n: number) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
}

function fmtCost(n: number) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

// ── Material row ──────────────────────────────────────────────────────────────

interface TaskMaterialRowProps {
  material: TaskMaterial
  taskId: string
  workOrderId: string
  taskStatus: string
}

function TaskMaterialRow({ material, taskId, workOrderId, taskStatus }: TaskMaterialRowProps) {
  const [inputValue, setInputValue] = useState(String(Number(material.consumed_quantity)))
  const [editing, setEditing] = useState(false)
  const consume = useConsumeMaterial()
  const remove = useRemoveMaterial()

  const canConsume = taskStatus === 'in_progress' || taskStatus === 'completed'
  const estimated = Number(material.estimated_quantity)
  const consumed = Number(material.consumed_quantity)
  const pct = estimated > 0 ? Math.min((consumed / estimated) * 100, 100) : 0
  const overConsumed = consumed > estimated

  const handleSave = async () => {
    const qty = parseFloat(inputValue.replace(',', '.'))
    if (isNaN(qty) || qty < 0) {
      setInputValue(String(consumed))
      setEditing(false)
      return
    }
    try {
      await consume.mutateAsync({ workOrderId, taskId, materialId: material.id, consumed_quantity: qty })
      setEditing(false)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleRemove = async () => {
    if (!confirm(`¿Eliminar "${material.inventory_item_name}" de esta tarea?`)) return
    try {
      await remove.mutateAsync({ workOrderId, taskId, materialId: material.id })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-800">
            {material.inventory_item_name}
          </p>
          <p className="text-xs text-gray-500">
            Est: {fmtQty(estimated)} {material.inventory_item_unit}
            {' · '}Coste: {fmtCost(Number(material.unit_cost))} €/ud
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {canConsume && (
            editing ? (
              <>
                <input
                  type="number"
                  min="0"
                  step="0.001"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSave()
                    if (e.key === 'Escape') { setInputValue(String(consumed)); setEditing(false) }
                  }}
                />
                <button
                  onClick={handleSave}
                  disabled={consume.isPending}
                  className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  OK
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-white"
              >
                Registrar
              </button>
            )
          )}

          {consumed === 0 && (
            <button
              onClick={handleRemove}
              disabled={remove.isPending}
              className="rounded p-1 text-gray-300 hover:text-red-500 disabled:opacity-50"
              title="Eliminar material"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      <div className="mt-2">
        <div className="mb-1 flex justify-between text-xs text-gray-500">
          <span>
            Consumido: {fmtQty(consumed)} / {fmtQty(estimated)} {material.inventory_item_unit}
          </span>
          {overConsumed && <span className="text-amber-600">Excedido</span>}
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className={`h-full rounded-full transition-all ${overConsumed ? 'bg-amber-500' : 'bg-green-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// ── Add material inline form ──────────────────────────────────────────────────

interface AddMaterialInlineFormProps {
  workOrderId: string
  taskId: string
  onClose: () => void
}

function AddMaterialInlineForm({ workOrderId, taskId, onClose }: AddMaterialInlineFormProps) {
  const [itemSearch, setItemSearch] = useState('')
  const [selectedItemId, setSelectedItemId] = useState('')
  const [selectedItemUnit, setSelectedItemUnit] = useState('')
  const [selectedItemCost, setSelectedItemCost] = useState('')
  const [qty, setQty] = useState('')
  const [unitCost, setUnitCost] = useState('')

  const { data: inventoryData } = useInventoryItems({ q: itemSearch || undefined, limit: 30 })
  const items = inventoryData?.items ?? []
  const addMaterial = useAddMaterial()

  const handleSubmit = async () => {
    if (!selectedItemId || !qty) return
    const qtyNum = parseFloat(qty.replace(',', '.'))
    if (isNaN(qtyNum) || qtyNum <= 0) return
    try {
      await addMaterial.mutateAsync({
        workOrderId,
        inventory_item_id: selectedItemId,
        task_id: taskId,
        estimated_quantity: qtyNum,
        unit_cost: unitCost ? parseFloat(unitCost.replace(',', '.')) : undefined,
      })
      onClose()
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2">
      <p className="text-xs font-semibold text-gray-700">Añadir material</p>

      <div className="relative">
        <input
          type="text"
          placeholder="Buscar artículo…"
          value={itemSearch}
          onChange={(e) => { setItemSearch(e.target.value); setSelectedItemId('') }}
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
          autoFocus
        />
        {items.length > 0 && !selectedItemId && (
          <div className="absolute z-20 mt-1 max-h-36 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-md">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setSelectedItemId(item.id)
                  setSelectedItemUnit(item.unit)
                  setSelectedItemCost(String(Number(item.unit_cost_avg || item.unit_cost)))
                  setUnitCost(String(Number(item.unit_cost_avg || item.unit_cost)))
                  setItemSearch(item.name)
                }}
                className="block w-full px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                <span className="font-medium">{item.name}</span>
                <span className="ml-2 text-xs text-gray-400">
                  {item.unit} · {fmtCost(Number(item.unit_cost_avg || item.unit_cost))} €/ud
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-gray-500 mb-0.5">
            Cantidad {selectedItemUnit ? `(${selectedItemUnit})` : ''}
          </label>
          <input
            type="number"
            min="0"
            step="0.001"
            placeholder="0.000"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-500 mb-0.5">Coste unitario (€)</label>
          <input
            type="number"
            min="0"
            step="0.0001"
            placeholder={selectedItemCost || '0.00'}
            value={unitCost}
            onChange={(e) => setUnitCost(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={!selectedItemId || !qty || addMaterial.isPending}
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {addMaterial.isPending ? 'Añadiendo…' : 'Añadir'}
        </button>
        <button
          onClick={onClose}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// ── Main list ─────────────────────────────────────────────────────────────────

interface TaskMaterialListProps {
  task: Task
  workOrderId: string
}

export function TaskMaterialList({ task, workOrderId }: TaskMaterialListProps) {
  const [showAddForm, setShowAddForm] = useState(false)

  return (
    <div className="space-y-2">
      {task.materials.map((m) => (
        <TaskMaterialRow
          key={m.id}
          material={m}
          taskId={task.id}
          workOrderId={workOrderId}
          taskStatus={task.status}
        />
      ))}

      {showAddForm ? (
        <AddMaterialInlineForm
          workOrderId={workOrderId}
          taskId={task.id}
          onClose={() => setShowAddForm(false)}
        />
      ) : (
        <button
          onClick={() => setShowAddForm(true)}
          className="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-gray-300 py-2 text-xs text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={12} />
          Añadir material
        </button>
      )}
    </div>
  )
}
