import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, ExternalLink, Trash2 } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useWorkOrderStore } from '../store/work-order-store'
import { useDeleteWorkOrder, useUpdateWorkOrderStatus } from '../hooks/use-work-orders'
import { WorkOrderStatusBadge } from './WorkOrderStatusBadge'
import { WorkOrderKPIPanel } from './WorkOrderKPIPanel'
import { TaskList } from './TaskList'
import { CertificationList } from './CertificationList'
import { WorkOrderPurchaseOrders } from './WorkOrderPurchaseOrders'
import { WorkOrderMaterials } from './WorkOrderMaterials'
import { DeliveryNoteList } from './DeliveryNoteList'
import type { WorkOrder, WorkOrderStatus } from '../types'

type Tab = 'resumen' | 'tareas' | 'materiales' | 'pedidos' | 'certificaciones' | 'albaranes' | 'notas'

const TABS: { id: Tab; label: string }[] = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'tareas', label: 'Tareas' },
  { id: 'materiales', label: 'Materiales' },
  { id: 'pedidos', label: 'Pedidos' },
  { id: 'certificaciones', label: 'Certificaciones' },
  { id: 'albaranes', label: 'Albaranes' },
  { id: 'notas', label: 'Notas' },
]

// Allowed manual status transitions per current status
const STATUS_BUTTONS: Partial<
  Record<WorkOrderStatus, { label: string; next: string; variant: string }[]>
> = {
  draft: [{ label: 'Iniciar obra', next: 'active', variant: 'primary' }],
  active: [
    { label: 'Marcar pendiente cierre', next: 'pending_closure', variant: 'amber' },
    { label: 'Cancelar obra', next: 'cancelled', variant: 'danger' },
  ],
  pending_closure: [
    { label: 'Cerrar obra', next: 'closed', variant: 'primary' },
    { label: 'Reabrir', next: 'active', variant: 'secondary' },
  ],
  closed: [
    { label: 'Reabrir obra', next: 'active', variant: 'secondary' },
  ],
}

const VARIANT_CLASSES: Record<string, string> = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700',
  secondary:
    'border border-gray-300 text-gray-700 hover:bg-gray-50',
  amber:
    'bg-amber-500 text-white hover:bg-amber-600',
  danger:
    'border border-red-300 text-red-600 hover:bg-red-50',
}

interface WorkOrderDetailProps {
  workOrder: WorkOrder
}

export function WorkOrderDetail({ workOrder }: WorkOrderDetailProps) {
  const navigate = useNavigate()
  const { activeTab, setActiveTab } = useWorkOrderStore()
  const updateStatus = useUpdateWorkOrderStatus()
  const deleteWorkOrder = useDeleteWorkOrder()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const handleDelete = () => {
    deleteWorkOrder.mutate(workOrder.id, {
      onSuccess: () => {
        setShowDeleteConfirm(false)
        navigate('/obras')
      },
    })
  }

  const handleOpenBudget = () => {
    if (!workOrder.origin_budget_id) return
    navigate(`/presupuestos/${workOrder.origin_budget_id}`)
  }

  const buttons = STATUS_BUTTONS[workOrder.status as WorkOrderStatus] ?? []

  const handleStatusChange = async (next: string) => {
    if (next === 'cancelled') {
      if (!confirm('¿Cancelar esta obra? Esta acción es irreversible.')) return
    }
    try {
      await updateStatus.mutateAsync({ id: workOrder.id, status: next })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-xl border border-gray-100 bg-white p-5">
        <button
          onClick={() => navigate('/obras')}
          className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft size={14} />
          Volver a obras
        </button>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-bold text-gray-900">
                {workOrder.work_order_number}
              </h1>
              <WorkOrderStatusBadge status={workOrder.status as WorkOrderStatus} />
            </div>
            <p className="mt-1 text-sm text-gray-600">
              {workOrder.customer_name}
              {workOrder.budget_number && (
                <>
                  <span className="mx-1.5 text-gray-300">·</span>
                  Presupuesto{' '}
                  <button
                    onClick={handleOpenBudget}
                    className="inline-flex items-center gap-0.5 font-medium text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    {workOrder.budget_number}
                    <ExternalLink size={11} className="mb-0.5" />
                  </button>
                </>
              )}
            </p>
            {workOrder.address && (
              <p className="mt-1 flex items-center gap-1 text-sm text-gray-500">
                <MapPin size={12} />
                {workOrder.address}
              </p>
            )}
          </div>

          {/* Status action buttons */}
          <div className="flex flex-wrap gap-2">
            {buttons.map(({ label, next, variant }) => (
              <button
                key={next}
                onClick={() => handleStatusChange(next)}
                disabled={updateStatus.isPending}
                className={`rounded-md px-3 py-2 text-sm font-medium disabled:opacity-50 ${VARIANT_CLASSES[variant]}`}
              >
                {label}
              </button>
            ))}
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <Trash2 size={14} />
              Eliminar
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto rounded-xl border border-gray-100 bg-white p-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === id
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="rounded-xl border border-gray-100 bg-white p-5">
        {activeTab === 'resumen' && (
          <WorkOrderKPIPanel kpis={workOrder.kpis} />
        )}

        {activeTab === 'tareas' && (
          <TaskList
            tasks={workOrder.tasks}
            workOrderId={workOrder.id}
            workOrderStatus={workOrder.status as WorkOrderStatus}
          />
        )}

        {activeTab === 'materiales' && (
          <WorkOrderMaterials workOrder={workOrder} />
        )}

        {activeTab === 'pedidos' && (
          <WorkOrderPurchaseOrders workOrder={workOrder} />
        )}

        {activeTab === 'certificaciones' && (
          <CertificationList
            workOrder={workOrder}
            customerEmail={workOrder.customer_email}
            customerPhone={workOrder.customer_phone}
          />
        )}

        {activeTab === 'albaranes' && (
          <DeliveryNoteList
            workOrder={workOrder}
            customerEmail={workOrder.customer_email}
            customerPhone={workOrder.customer_phone}
          />
        )}

        {activeTab === 'notas' && (
          <div className="space-y-4">
            {workOrder.other_lines_notes && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Partidas sin estructura
                </p>
                <pre className="whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
                  {workOrder.other_lines_notes}
                </pre>
              </div>
            )}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Notas de la obra
              </p>
              <p className="text-sm text-gray-600">
                {workOrder.notes || (
                  <span className="text-gray-400">Sin notas.</span>
                )}
              </p>
            </div>
          </div>
        )}
      </div>

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white shadow-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                <Trash2 size={18} className="text-red-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Eliminar obra</h3>
                <p className="text-xs text-gray-500">
                  {workOrder.work_order_number}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              Esta acción es permanente y no se puede deshacer. Se eliminarán las
              tareas, certificaciones y albaranes asociados, y se liberará el stock
              reservado. ¿Confirmas que quieres eliminar esta obra?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteWorkOrder.isPending}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteWorkOrder.isPending}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteWorkOrder.isPending ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
