import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { useCreateInvoiceFromWorkOrder } from '../hooks/use-invoices'
import type { InvoiceLineCreatePayload } from '../types'

interface CertItem {
  id: string
  task_id: string
  amount: number
  notes?: string | null
  task?: { name: string }
}

interface Cert {
  id: string
  certification_number: string
  status: string
  items: CertItem[]
}

interface Task {
  id: string
  name: string
  status: string
  unit_price?: number | null
}

interface WorkOrderOption {
  id: string
  work_order_number: string
  status: string
  customer_id: string
}

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function today() {
  return new Date().toISOString().split('T')[0]
}

interface Props {
  preselectedWorkOrderId?: string
  preselectedCertificationIds?: string[]
  onSuccess: (invoiceId: string) => void
  onCancel: () => void
}

export function InvoiceFromWorkOrderForm({
  preselectedWorkOrderId,
  preselectedCertificationIds = [],
  onSuccess,
  onCancel,
}: Props) {
  const [step, setStep] = useState<1 | 2>(preselectedWorkOrderId ? 2 : 1)
  const [workOrderId, setWorkOrderId] = useState(preselectedWorkOrderId ?? '')
  const [workOrders, setWorkOrders] = useState<WorkOrderOption[]>([])
  const [certs, setCerts] = useState<Cert[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedCertIds, setSelectedCertIds] = useState<Set<string>>(
    new Set(preselectedCertificationIds),
  )
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set())
  const [extraLines, setExtraLines] = useState<InvoiceLineCreatePayload[]>([])
  const [discountPct, setDiscountPct] = useState('0')
  const [dueDate, setDueDate] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  const { mutate, isPending, error } = useCreateInvoiceFromWorkOrder()

  // Load work orders for step 1
  useEffect(() => {
    if (preselectedWorkOrderId) return
    apiClient
      .get('/api/v1/work-orders', { params: { limit: 200 } })
      .then(({ data }) =>
        setWorkOrders(
          (data.items ?? []).filter((o: WorkOrderOption) =>
            ['active', 'pending_closure'].includes(o.status),
          ),
        ),
      )
  }, [preselectedWorkOrderId])

  // Load certifications + tasks when work order is selected
  useEffect(() => {
    if (!workOrderId) return
    setLoading(true)
    Promise.all([
      apiClient.get(`/api/v1/work-orders/${workOrderId}`),
    ])
      .then(([{ data }]) => {
        const issuedCerts: Cert[] = (data.certifications ?? []).filter(
          (c: Cert) => c.status === 'issued',
        )
        setCerts(issuedCerts)

        // Tasks completed but not in an invoiced certification
        const invoicedTaskIds = new Set(
          (data.certifications ?? [])
            .filter((c: Cert) => c.status === 'invoiced')
            .flatMap((c: Cert) => c.items.map((i) => i.task_id)),
        )
        const completedTasks: Task[] = (data.tasks ?? []).filter(
          (t: Task) => t.status === 'completed' && !invoicedTaskIds.has(t.id),
        )
        setTasks(completedTasks)
      })
      .finally(() => setLoading(false))
  }, [workOrderId])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate(
      {
        work_order_id: workOrderId,
        certification_ids: Array.from(selectedCertIds),
        task_ids: Array.from(selectedTaskIds),
        extra_lines: extraLines.filter((l) => l.description),
        discount_pct: parseFloat(discountPct) || 0,
        due_date: dueDate || null,
        notes: notes || null,
      },
      { onSuccess: (data) => onSuccess(data.id) },
    )
  }

  function certTotal(cert: Cert) {
    return cert.items.reduce((s, i) => s + i.amount, 0)
  }

  function addExtraLine() {
    setExtraLines((prev) => [
      ...prev,
      { origin_type: 'manual', description: '', quantity: 1, unit_price: 0 },
    ])
  }

  // ── Step 1: pick work order ───────────────────────────────────────────────
  if (step === 1) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-700">
          Seleccionar obra
        </h3>
        {workOrders.length === 0 ? (
          <p className="text-sm text-gray-400">
            No hay obras activas o en cierre pendiente
          </p>
        ) : (
          <div className="max-h-80 overflow-y-auto divide-y divide-gray-100 rounded border border-gray-200">
            {workOrders.map((wo) => (
              <button
                key={wo.id}
                onClick={() => {
                  setWorkOrderId(wo.id)
                  setStep(2)
                }}
                className="w-full px-3 py-2 text-left text-sm hover:bg-blue-50"
              >
                <span className="font-medium">{wo.work_order_number}</span>
                <span className="ml-2 text-xs text-gray-500">
                  {wo.status === 'pending_closure'
                    ? 'Pendiente cierre'
                    : 'En ejecución'}
                </span>
              </button>
            ))}
          </div>
        )}
        <div className="flex justify-end">
          <button
            onClick={onCancel}
            className="rounded px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  // ── Step 2: pick content ──────────────────────────────────────────────────
  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {loading && (
        <div className="text-center text-sm text-gray-400">Cargando…</div>
      )}

      {/* Certifications */}
      {certs.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Certificaciones emitidas disponibles
          </p>
          <div className="divide-y divide-gray-100 rounded border border-gray-200">
            {certs.map((cert) => (
              <label
                key={cert.id}
                className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  checked={selectedCertIds.has(cert.id)}
                  onChange={(e) =>
                    setSelectedCertIds((prev) => {
                      const next = new Set(prev)
                      if (e.target.checked) next.add(cert.id)
                      else next.delete(cert.id)
                      return next
                    })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">
                    {cert.certification_number}
                  </p>
                  <p className="text-xs text-gray-500">
                    {cert.items.length} tarea(s) · {fmt(certTotal(cert))} €
                  </p>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Tasks without certification */}
      {tasks.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Tareas completadas sin certificar
          </p>
          <p className="mb-2 text-xs text-amber-600">
            Estas tareas no tienen certificación previa.
          </p>
          <div className="divide-y divide-gray-100 rounded border border-gray-200">
            {tasks.map((task) => (
              <label
                key={task.id}
                className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  checked={selectedTaskIds.has(task.id)}
                  onChange={(e) =>
                    setSelectedTaskIds((prev) => {
                      const next = new Set(prev)
                      if (e.target.checked) next.add(task.id)
                      else next.delete(task.id)
                      return next
                    })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                <div className="flex-1">
                  <p className="text-sm text-gray-800">{task.name}</p>
                  {task.unit_price != null && (
                    <p className="text-xs text-gray-500">
                      {fmt(task.unit_price)} €
                    </p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Extra lines */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Conceptos adicionales
        </p>
        {extraLines.map((line, i) => (
          <div key={i} className="mb-2 flex gap-2">
            <input
              placeholder="Descripción"
              value={line.description}
              onChange={(e) =>
                setExtraLines((prev) =>
                  prev.map((l, j) =>
                    j === i ? { ...l, description: e.target.value } : l,
                  ),
                )
              }
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
            />
            <input
              type="number"
              placeholder="€"
              value={line.unit_price}
              onChange={(e) =>
                setExtraLines((prev) =>
                  prev.map((l, j) =>
                    j === i
                      ? { ...l, unit_price: parseFloat(e.target.value) }
                      : l,
                  ),
                )
              }
              className="w-20 rounded border border-gray-300 px-2 py-1 text-right text-xs"
            />
            <button
              type="button"
              onClick={() =>
                setExtraLines((prev) => prev.filter((_, j) => j !== i))
              }
              className="text-xs text-red-400 hover:text-red-600"
            >
              ✕
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={addExtraLine}
          className="text-xs text-blue-600 hover:text-blue-700"
        >
          + Añadir concepto adicional
        </button>
      </div>

      {/* Settings */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Descuento global (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={discountPct}
            onChange={(e) => setDiscountPct(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Fecha de vencimiento
          </label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">
          Notas internas
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
        />
      </div>

      {error && (
        <p className="text-xs text-red-600">
          {(error as any).response?.data?.detail ?? 'Error al crear la factura'}
        </p>
      )}

      <div className="flex justify-between gap-2">
        {!preselectedWorkOrderId && (
          <button
            type="button"
            onClick={() => setStep(1)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            ← Cambiar obra
          </button>
        )}
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={
              isPending ||
              (selectedCertIds.size === 0 &&
                selectedTaskIds.size === 0 &&
                extraLines.filter((l) => l.description).length === 0)
            }
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? 'Creando…' : 'Crear factura'}
          </button>
        </div>
      </div>
    </form>
  )
}
