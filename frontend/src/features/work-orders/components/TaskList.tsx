import { useState } from 'react'
import { Plus } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useAddTask } from '../hooks/use-work-order-tasks'
import { TaskCard } from './TaskCard'
import type { Task, WorkOrderStatus } from '../types'

interface TaskListProps {
  tasks: Task[]
  workOrderId: string
  workOrderStatus: WorkOrderStatus
}

export function TaskList({ tasks, workOrderId, workOrderStatus }: TaskListProps) {
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [hours, setHours] = useState('')
  const addTask = useAddTask()

  const canAdd = !['closed', 'cancelled'].includes(workOrderStatus)

  const handleAdd = async () => {
    if (!name.trim()) return
    try {
      await addTask.mutateAsync({
        workOrderId,
        name: name.trim(),
        unit_price: price ? parseFloat(price.replace(',', '.')) : undefined,
        estimated_hours: hours ? parseFloat(hours.replace(',', '.')) : undefined,
      })
      setName('')
      setPrice('')
      setHours('')
      setShowForm(false)
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const sorted = [...tasks].sort((a, b) => a.sort_order - b.sort_order)

  return (
    <div className="space-y-3">
      {sorted.length === 0 && !showForm && (
        <p className="py-8 text-center text-sm text-gray-400">
          No hay tareas en esta obra.
        </p>
      )}

      {sorted.map((task) => (
        <TaskCard key={task.id} task={task} workOrderId={workOrderId} />
      ))}

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="mb-3 text-sm font-medium text-gray-700">
            Nueva tarea
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              placeholder="Nombre de la tarea"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAdd()
                if (e.key === 'Escape') setShowForm(false)
              }}
            />
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Precio (€)"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-28 rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <input
              type="number"
              min="0"
              step="0.5"
              placeholder="Horas est."
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="w-28 rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <button
              onClick={handleAdd}
              disabled={!name.trim() || addTask.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Añadir
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {canAdd && !showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={14} />
          Añadir tarea
        </button>
      )}
    </div>
  )
}
