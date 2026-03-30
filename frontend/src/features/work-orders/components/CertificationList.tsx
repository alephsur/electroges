import { useEffect, useState } from 'react'
import { Plus, Send, Trash2 } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import {
  useCertifiableTasks,
  useCreateCertification,
  useDeleteCertification,
  useIssueCertification,
} from '../hooks/use-certifications'
import type { Certification, WorkOrder } from '../types'

function fmt(n: number) {
  return n.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const CERT_STATUS: Record<string, { label: string; className: string }> = {
  draft: { label: 'Borrador', className: 'bg-gray-100 text-gray-700' },
  issued: { label: 'Emitida', className: 'bg-blue-100 text-blue-700' },
  invoiced: { label: 'Facturada', className: 'bg-green-100 text-green-700' },
}

interface CertificationFormProps {
  workOrderId: string
  onClose: () => void
}

function CertificationForm({ workOrderId, onClose }: CertificationFormProps) {
  const { data: certifiable = [] } = useCertifiableTasks(workOrderId)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  // per-task amount overrides (task.id → string input)
  const [amounts, setAmounts] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState('')
  const createCert = useCreateCertification()

  // Pydantic serializes Decimal as string — always coerce to number
  const toNum = (v: unknown): number => {
    const n = Number(v)
    return isNaN(n) ? 0 : n
  }

  const defaultAmount = (task: { unit_price: number | null; estimated_cost: number }) =>
    toNum(task.unit_price ?? task.estimated_cost)

  // Pre-populate amounts when tasks load so state values are always strings of numbers
  useEffect(() => {
    if (certifiable.length === 0) return
    setAmounts((prev) => {
      const next: Record<string, string> = { ...prev }
      for (const task of certifiable) {
        if (next[task.id] === undefined) {
          next[task.id] = String(defaultAmount(task))
        }
      }
      return next
    })
  }, [certifiable])

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const setAmount = (id: string, val: string) =>
    setAmounts((prev) => ({ ...prev, [id]: val }))

  const resolveAmount = (task: { id: string; unit_price: number | null; estimated_cost: number }): number => {
    const raw = amounts[task.id]
    if (raw !== undefined && raw !== '') {
      const parsed = parseFloat(raw.replace(',', '.'))
      return isNaN(parsed) ? defaultAmount(task) : parsed
    }
    return defaultAmount(task)
  }

  const selectedTasks = certifiable.filter((t) => selected.has(t.id))
  const total = selectedTasks.reduce((acc, t) => acc + resolveAmount(t), 0)

  const handleCreate = async () => {
    if (selected.size === 0) return
    try {
      await createCert.mutateAsync({
        workOrderId,
        items: [...selected].map((id) => {
          const task = certifiable.find((t) => t.id === id)!
          const amount = resolveAmount(task)
          return { task_id: id, amount }
        }),
        notes: notes || undefined,
      })
      onClose()
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
      <p className="mb-3 text-sm font-semibold text-gray-800">
        Nueva certificación
      </p>
      {certifiable.length === 0 ? (
        <p className="text-sm text-gray-500">
          No hay tareas completadas pendientes de certificar.
        </p>
      ) : (
        <>
          <div className="mb-3 space-y-2">
            {certifiable.map((task) => (
              <div
                key={task.id}
                className="flex items-center gap-3 rounded-lg border border-white bg-white px-3 py-2"
              >
                <input
                  type="checkbox"
                  checked={selected.has(task.id)}
                  onChange={() => toggle(task.id)}
                  className="rounded"
                />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">
                    {task.name}
                  </p>
                </div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={amounts[task.id] ?? ''}
                  onChange={(e) => setAmount(task.id, e.target.value)}
                  disabled={!selected.has(task.id)}
                  className="w-28 rounded border border-gray-300 px-2 py-1 text-right text-sm disabled:bg-gray-50 disabled:text-gray-400"
                />
                <span className="shrink-0 text-sm text-gray-500">€</span>
              </div>
            ))}
          </div>
          {selected.size > 0 && (
            <p className="mb-3 text-sm font-medium text-gray-700">
              Total seleccionado:{' '}
              <strong>{fmt(total)} €</strong>
            </p>
          )}
          <textarea
            placeholder="Notas (opcional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mb-3 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={selected.size === 0 || createCert.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Crear certificación
            </button>
            <button
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancelar
            </button>
          </div>
        </>
      )}
    </div>
  )
}

interface CertificationListProps {
  workOrder: WorkOrder
}

export function CertificationList({ workOrder }: CertificationListProps) {
  const [showForm, setShowForm] = useState(false)
  const issueCert = useIssueCertification()
  const deleteCert = useDeleteCertification()

  const certified = workOrder.kpis.total_certified
  const total = workOrder.kpis.budget_total
  const pct = total > 0 ? Math.min((certified / total) * 100, 100) : 0

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div>
        <div className="mb-1 flex justify-between text-sm">
          <span className="text-gray-600">Certificado</span>
          <span className="font-medium">
            {fmt(certified)}€ / {fmt(total)}€
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-blue-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* List */}
      {workOrder.certifications.length === 0 && !showForm && (
        <p className="py-4 text-center text-sm text-gray-400">
          No hay certificaciones aún.
        </p>
      )}

      {workOrder.certifications.map((cert) => {
        const cfg = CERT_STATUS[cert.status] ?? CERT_STATUS.draft
        return (
          <div
            key={cert.id}
            className="rounded-xl border border-gray-100 bg-white p-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">
                    {cert.certification_number}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}
                  >
                    {cfg.label}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {cert.items.length} tarea
                  {cert.items.length !== 1 ? 's' : ''} ·{' '}
                  <strong>{fmt(cert.total_amount)}€</strong>
                </p>
                {cert.notes && (
                  <p className="mt-1 text-xs text-gray-400">{cert.notes}</p>
                )}
              </div>
              <div className="flex gap-2">
                {cert.status === 'draft' && (
                  <>
                    <button
                      onClick={async () => {
                        try {
                          await issueCert.mutateAsync({
                            workOrderId: workOrder.id,
                            certId: cert.id,
                          })
                        } catch (e) {
                          alert(getApiErrorMessage(e))
                        }
                      }}
                      title="Emitir certificación"
                      className="rounded-md border border-blue-300 p-1.5 text-blue-600 hover:bg-blue-50"
                    >
                      <Send size={14} />
                    </button>
                    <button
                      onClick={async () => {
                        if (
                          !confirm(
                            '¿Eliminar esta certificación? Esta acción no se puede deshacer.',
                          )
                        )
                          return
                        try {
                          await deleteCert.mutateAsync({
                            workOrderId: workOrder.id,
                            certId: cert.id,
                          })
                        } catch (e) {
                          alert(getApiErrorMessage(e))
                        }
                      }}
                      title="Eliminar"
                      className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50"
                    >
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Items */}
            {cert.items.length > 0 && (
              <div className="mt-3 space-y-1 border-t border-gray-100 pt-3">
                {cert.items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span className="text-gray-600 truncate">{item.task_name}</span>
                    <span className="shrink-0 font-medium">
                      {fmt(item.amount)}€
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {showForm && (
        <CertificationForm
          workOrderId={workOrder.id}
          onClose={() => setShowForm(false)}
        />
      )}

      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={14} />
          Nueva certificación
        </button>
      )}
    </div>
  )
}
