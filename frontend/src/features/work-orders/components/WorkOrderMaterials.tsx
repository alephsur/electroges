import { useState } from 'react'
import { Package, Plus, Trash2 } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useInventoryItems } from '@/features/inventory/hooks/use-inventory-items'
import { useAddMaterial, useConsumeMaterial, useRemoveMaterial } from '../hooks/use-work-order-tasks'
import type { Task, TaskMaterial, WorkOrder } from '../types'

function fmt(n: number) {
  return Number(n).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtQty(n: number) {
  return Number(n).toLocaleString('es-ES', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  })
}

// ── Add material form ────────────────────────────────────────────────────────

interface AddMaterialFormProps {
  workOrderId: string
  tasks: Task[]
  onClose: () => void
}

function AddMaterialForm({ workOrderId, tasks, onClose }: AddMaterialFormProps) {
  const [itemSearch, setItemSearch] = useState('')
  const [selectedItemId, setSelectedItemId] = useState('')
  const [selectedItemUnit, setSelectedItemUnit] = useState('')
  const [selectedItemCost, setSelectedItemCost] = useState('')
  const [taskId, setTaskId] = useState(tasks[0]?.id ?? '')
  const [qty, setQty] = useState('')
  const [unitCost, setUnitCost] = useState('')

  const { data: inventoryData } = useInventoryItems({
    q: itemSearch || undefined,
    limit: 50,
  })
  const items = inventoryData?.items ?? []

  const addMaterial = useAddMaterial()

  const handleSubmit = async () => {
    if (!selectedItemId || !taskId || !qty) return
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
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-3">
      <p className="text-sm font-semibold text-gray-800">Añadir material</p>

      {/* Inventory item search */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Artículo de inventario
        </label>
        <input
          type="text"
          placeholder="Buscar artículo…"
          value={itemSearch}
          onChange={(e) => {
            setItemSearch(e.target.value)
            setSelectedItemId('')
          }}
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
          autoFocus
        />
        {items.length > 0 && !selectedItemId && (
          <div className="mt-1 max-h-36 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-sm">
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
                className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                <span className="font-medium">{item.name}</span>
                <span className="ml-2 text-xs text-gray-400">
                  {item.unit} · {fmt(Number(item.unit_cost_avg || item.unit_cost))} €/ud
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Task selector */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Asignar a tarea
        </label>
        <select
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
        >
          {tasks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {/* Quantity + unit cost */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Cantidad est. {selectedItemUnit ? `(${selectedItemUnit})` : ''}
          </label>
          <input
            type="number"
            min="0"
            step="0.001"
            placeholder="0.000"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Coste unitario (€)
          </label>
          <input
            type="number"
            min="0"
            step="0.0001"
            placeholder={selectedItemCost || '0.00'}
            value={unitCost}
            onChange={(e) => setUnitCost(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <button
          onClick={handleSubmit}
          disabled={!selectedItemId || !taskId || !qty || addMaterial.isPending}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {addMaterial.isPending ? 'Añadiendo…' : 'Añadir'}
        </button>
        <button
          onClick={onClose}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// ── Material row ─────────────────────────────────────────────────────────────

interface MaterialRowProps {
  material: TaskMaterial
  task: Task
  workOrderId: string
}

function MaterialRow({ material, task, workOrderId }: MaterialRowProps) {
  const [editing, setEditing] = useState(false)
  const [consumeInput, setConsumeInput] = useState(String(Number(material.consumed_quantity)))
  const consume = useConsumeMaterial()
  const remove = useRemoveMaterial()

  const canConsume = task.status === 'in_progress' || task.status === 'completed'
  const estimated = Number(material.estimated_quantity)
  const consumed = Number(material.consumed_quantity)
  const pct = estimated > 0 ? Math.min((consumed / estimated) * 100, 100) : 0
  const over = consumed > estimated

  const handleSave = async () => {
    const qty = parseFloat(consumeInput.replace(',', '.'))
    if (isNaN(qty) || qty < 0) {
      setConsumeInput(String(consumed))
      setEditing(false)
      return
    }
    try {
      await consume.mutateAsync({
        workOrderId,
        taskId: task.id,
        materialId: material.id,
        consumed_quantity: qty,
      })
      setEditing(false)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleRemove = async () => {
    if (!confirm(`¿Eliminar "${material.inventory_item_name}" de la tarea "${task.name}"?`)) return
    try {
      await remove.mutateAsync({ workOrderId, taskId: task.id, materialId: material.id })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <tr className="border-b border-gray-50 last:border-0">
      <td className="py-2.5 pr-3">
        <p className="text-sm font-medium text-gray-800">{material.inventory_item_name}</p>
        <p className="text-xs text-gray-400">{material.inventory_item_unit}</p>
      </td>
      <td className="py-2.5 pr-3 text-xs text-gray-500">{task.name}</td>
      <td className="py-2.5 pr-3 text-right text-sm text-gray-700">
        {fmtQty(estimated)}
      </td>
      <td className="py-2.5 pr-3">
        {canConsume ? (
          editing ? (
            <div className="flex items-center gap-1">
              <input
                type="number"
                min="0"
                step="0.001"
                value={consumeInput}
                onChange={(e) => setConsumeInput(e.target.value)}
                className="w-20 rounded border border-gray-300 px-2 py-0.5 text-xs text-right"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSave()
                  if (e.key === 'Escape') {
                    setConsumeInput(String(consumed))
                    setEditing(false)
                  }
                }}
              />
              <button
                onClick={handleSave}
                disabled={consume.isPending}
                className="rounded bg-blue-600 px-1.5 py-0.5 text-xs text-white disabled:opacity-50"
              >
                OK
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className={`text-sm font-medium hover:underline ${over ? 'text-amber-600' : 'text-gray-700'}`}
            >
              {fmtQty(consumed)}
              {over && <span className="ml-1 text-xs">⚠</span>}
            </button>
          )
        ) : (
          <span className="text-sm text-gray-400">{fmtQty(consumed)}</span>
        )}
      </td>
      <td className="py-2.5 pr-3">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full rounded-full ${over ? 'bg-amber-500' : 'bg-green-500'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-xs text-gray-400">{Math.round(pct)}%</span>
        </div>
      </td>
      <td className="py-2.5 pr-3 text-right text-sm text-gray-600">
        {fmt(Number(material.unit_cost))} €
      </td>
      <td className="py-2.5 pr-3 text-right text-sm text-gray-700">
        {fmt(Number(material.estimated_cost))} €
      </td>
      <td className="py-2.5 text-right text-sm font-medium text-gray-900">
        {fmt(Number(material.actual_cost))} €
      </td>
      <td className="py-2.5 pl-3">
        {consumed === 0 && (
          <button
            onClick={handleRemove}
            disabled={remove.isPending}
            className="rounded p-1 text-gray-300 hover:text-red-500 disabled:opacity-50"
            title="Eliminar material"
          >
            <Trash2 size={14} />
          </button>
        )}
      </td>
    </tr>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

interface WorkOrderMaterialsProps {
  workOrder: WorkOrder
}

export function WorkOrderMaterials({ workOrder }: WorkOrderMaterialsProps) {
  const [showForm, setShowForm] = useState(false)

  const activeTasks = workOrder.tasks.filter(
    (t) => t.status !== 'cancelled',
  )
  const allMaterials: { material: TaskMaterial; task: Task }[] = activeTasks.flatMap(
    (task) => task.materials.map((m) => ({ material: m, task })),
  )

  const totalEstimated = allMaterials.reduce(
    (acc, { material }) => acc + Number(material.estimated_cost),
    0,
  )
  const totalActual = allMaterials.reduce(
    (acc, { material }) => acc + Number(material.actual_cost),
    0,
  )

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-gray-50 px-4 py-3">
          <p className="text-xs text-gray-500">Artículos</p>
          <p className="text-lg font-semibold text-gray-900">{allMaterials.length}</p>
        </div>
        <div className="rounded-lg bg-gray-50 px-4 py-3">
          <p className="text-xs text-gray-500">Coste estimado</p>
          <p className="text-lg font-semibold text-gray-900">{fmt(totalEstimated)} €</p>
        </div>
        <div className="rounded-lg bg-gray-50 px-4 py-3">
          <p className="text-xs text-gray-500">Coste real</p>
          <p className="text-lg font-semibold text-gray-900">{fmt(totalActual)} €</p>
        </div>
      </div>

      {/* Materials table */}
      {allMaterials.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-gray-100">
          <table className="w-full text-left">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-xs font-medium text-gray-500">Material</th>
                <th className="px-3 py-2 text-xs font-medium text-gray-500">Tarea</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Est.</th>
                <th className="px-3 py-2 text-xs font-medium text-gray-500">Consumido</th>
                <th className="px-3 py-2 text-xs font-medium text-gray-500">Progreso</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">€/ud</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Coste est.</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Coste real</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 bg-white px-3">
              {allMaterials.map(({ material, task }) => (
                <MaterialRow
                  key={material.id}
                  material={material}
                  task={task}
                  workOrderId={workOrder.id}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !showForm && (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <Package size={32} className="mb-2 text-gray-200" />
            <p className="text-sm text-gray-400">No hay materiales en esta obra.</p>
          </div>
        )
      )}

      {/* Add form */}
      {showForm && activeTasks.length > 0 && (
        <AddMaterialForm
          workOrderId={workOrder.id}
          tasks={activeTasks}
          onClose={() => setShowForm(false)}
        />
      )}

      {activeTasks.length === 0 && (
        <p className="text-sm text-amber-600">
          Crea al menos una tarea antes de añadir materiales.
        </p>
      )}

      {/* Add button */}
      {!showForm && activeTasks.length > 0 && (
        <button
          onClick={() => setShowForm(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={14} />
          Añadir material
        </button>
      )}
    </div>
  )
}
