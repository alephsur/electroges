import { useState } from 'react'
import { ChevronDown, ChevronRight, Clock, Pencil, X, Check } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useUpdateTask, useUpdateTaskStatus } from '../hooks/use-work-order-tasks'
import { TaskMaterialList } from './TaskMaterialList'
import type { Task, TaskStatus } from '../types'

function fmt(n: number) {
  return n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: 'Pendiente',
  in_progress: 'En progreso',
  completed: 'Completada',
  cancelled: 'Cancelada',
}

const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

const STATUS_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  pending: ['in_progress', 'cancelled'],
  in_progress: ['completed', 'pending', 'cancelled'],
  completed: ['in_progress'],
  cancelled: [],
}

interface TaskCardProps {
  task: Task
  workOrderId: string
}

export function TaskCard({ task, workOrderId }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [showStatusMenu, setShowStatusMenu] = useState(false)
  const [actualHoursInput, setActualHoursInput] = useState(String(task.actual_hours ?? ''))
  const [pendingStatus, setPendingStatus] = useState<TaskStatus | null>(null)

  // ── Price editing ──
  const [editingPrice, setEditingPrice] = useState(false)
  const [priceInput, setPriceInput] = useState(
    task.unit_price != null ? String(Number(task.unit_price)) : '',
  )

  // ── Task text editing ──
  const [editingTask, setEditingTask] = useState(false)
  const [nameInput, setNameInput] = useState(task.name)
  const [descInput, setDescInput] = useState(task.description ?? '')
  const [hoursInput, setHoursInput] = useState(
    task.estimated_hours != null ? String(Number(task.estimated_hours)) : '',
  )

  const updateStatus = useUpdateTaskStatus()
  const updateTask = useUpdateTask()

  const transitions = STATUS_TRANSITIONS[task.status] ?? []

  const handleStatusChange = async (newStatus: TaskStatus) => {
    if (newStatus === 'completed') {
      setPendingStatus(newStatus)
      setShowStatusMenu(false)
      return
    }
    setShowStatusMenu(false)
    try {
      await updateStatus.mutateAsync({ workOrderId, taskId: task.id, status: newStatus })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleSavePrice = async () => {
    const val = parseFloat(priceInput.replace(',', '.'))
    const unit_price = isNaN(val) ? null : val
    try {
      await updateTask.mutateAsync({ workOrderId, taskId: task.id, unit_price })
      setEditingPrice(false)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleSaveTask = async () => {
    const name = nameInput.trim()
    if (!name) return
    const estHours = parseFloat(hoursInput.replace(',', '.'))
    try {
      await updateTask.mutateAsync({
        workOrderId,
        taskId: task.id,
        name,
        description: descInput.trim() || undefined,
        estimated_hours: isNaN(estHours) ? undefined : estHours,
      })
      setEditingTask(false)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleCancelTaskEdit = () => {
    setNameInput(task.name)
    setDescInput(task.description ?? '')
    setHoursInput(task.estimated_hours != null ? String(Number(task.estimated_hours)) : '')
    setEditingTask(false)
  }

  const handleConfirmComplete = async () => {
    const hours = parseFloat(actualHoursInput.replace(',', '.'))
    try {
      await updateStatus.mutateAsync({
        workOrderId,
        taskId: task.id,
        status: 'completed',
        actual_hours: isNaN(hours) ? undefined : hours,
      })
      setPendingStatus(null)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white">
      <div className="flex items-start gap-3 p-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-0.5 shrink-0 text-gray-400 hover:text-gray-600"
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>

        <div className="min-w-0 flex-1">
          {editingTask ? (
            /* ── Task edit form ── */
            <div className="space-y-2">
              <input
                type="text"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder="Nombre de la tarea"
                className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm font-medium focus:border-blue-400 focus:outline-none"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Escape') handleCancelTaskEdit() }}
              />
              <input
                type="text"
                value={descInput}
                onChange={(e) => setDescInput(e.target.value)}
                placeholder="Descripción (opcional)"
                className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-600 focus:border-blue-400 focus:outline-none"
              />
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 shrink-0">Horas estimadas:</label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={hoursInput}
                  onChange={(e) => setHoursInput(e.target.value)}
                  placeholder="0.0"
                  className="w-24 rounded-md border border-gray-300 px-2 py-1 text-sm"
                />
              </div>
              <div className="flex gap-2 pt-0.5">
                <button
                  onClick={handleSaveTask}
                  disabled={!nameInput.trim() || updateTask.isPending}
                  className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <Check size={12} />
                  Guardar
                </button>
                <button
                  onClick={handleCancelTaskEdit}
                  className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                >
                  <X size={12} />
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            /* ── Normal display ── */
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-gray-900">{task.name}</span>
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${TASK_STATUS_COLORS[task.status]}`}>
                  {TASK_STATUS_LABELS[task.status]}
                </span>
                {task.is_certified && (
                  <span className="inline-flex rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                    Certificada
                  </span>
                )}
                <button
                  onClick={() => setEditingTask(true)}
                  className="text-gray-300 hover:text-gray-500"
                  title="Editar tarea"
                >
                  <Pencil size={12} />
                </button>
              </div>

              {task.description && (
                <p className="mt-1 text-sm text-gray-500">{task.description}</p>
              )}

              {/* Unit price — editable inline */}
              <div className="mt-1 flex items-center gap-1.5">
                {editingPrice ? (
                  <>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={priceInput}
                      onChange={(e) => setPriceInput(e.target.value)}
                      className="w-28 rounded border border-gray-300 px-2 py-0.5 text-xs"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSavePrice()
                        if (e.key === 'Escape') {
                          setPriceInput(String(task.unit_price ?? ''))
                          setEditingPrice(false)
                        }
                      }}
                    />
                    <button
                      onClick={handleSavePrice}
                      disabled={updateTask.isPending}
                      className="rounded bg-blue-600 px-2 py-0.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      OK
                    </button>
                    <button
                      onClick={() => { setPriceInput(String(task.unit_price ?? '')); setEditingPrice(false) }}
                      className="text-xs text-gray-400 hover:text-gray-600"
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setEditingPrice(true)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                  >
                    <span className="font-medium">
                      {task.unit_price != null ? `${fmt(Number(task.unit_price))} €` : 'Sin precio'}
                    </span>
                    <Pencil size={10} className="text-gray-400" />
                  </button>
                )}
              </div>

              <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-500">
                {task.estimated_hours != null && (
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    Est: {task.estimated_hours}h
                    {task.actual_hours != null && ` · Real: ${task.actual_hours}h`}
                  </span>
                )}
                {task.materials.length > 0 && (
                  <span>{task.materials.length} material{task.materials.length !== 1 ? 'es' : ''}</span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Status change button */}
        {!editingTask && transitions.length > 0 && (
          <div className="relative shrink-0">
            <button
              onClick={() => setShowStatusMenu(!showStatusMenu)}
              className="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
            >
              Cambiar estado
            </button>
            {showStatusMenu && (
              <div className="absolute right-0 top-8 z-10 w-40 rounded-lg border border-gray-100 bg-white shadow-lg">
                {transitions.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleStatusChange(s)}
                    className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    {TASK_STATUS_LABELS[s]}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Complete confirmation (requires actual hours) */}
      {pendingStatus === 'completed' && (
        <div className="border-t border-gray-100 px-4 py-3">
          <p className="mb-2 text-sm font-medium text-gray-700">Horas reales de trabajo</p>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              step="0.5"
              placeholder="0.0"
              value={actualHoursInput}
              onChange={(e) => setActualHoursInput(e.target.value)}
              className="w-28 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              autoFocus
            />
            <button
              onClick={handleConfirmComplete}
              disabled={updateStatus.isPending}
              className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Completar
            </button>
            <button
              onClick={() => setPendingStatus(null)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Materials section — always shown when expanded */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Materiales
          </p>
          <TaskMaterialList task={task} workOrderId={workOrderId} />
        </div>
      )}
    </div>
  )
}
