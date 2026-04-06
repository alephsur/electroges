import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams, useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { useWorkOrder, useWorkOrders } from '../hooks/use-work-orders'
import { useWorkOrderStore } from '../store/work-order-store'
import { WorkOrderList } from './WorkOrderList'
import { WorkOrderDetail } from './WorkOrderDetail'
import { NewWorkOrderModal } from './NewWorkOrderModal'
import type { WorkOrderStatus } from '../types'

const STATUS_OPTIONS: { value: WorkOrderStatus | ''; label: string }[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'draft', label: 'Borrador' },
  { value: 'active', label: 'En ejecución' },
  { value: 'pending_closure', label: 'Pendiente cierre' },
  { value: 'closed', label: 'Cerrada' },
  { value: 'cancelled', label: 'Cancelada' },
]

function WorkOrderDetailRoute() {
  const { workOrderId } = useParams<{ workOrderId: string }>()
  const { setActiveTab } = useWorkOrderStore()
  const { data: workOrder, isLoading } = useWorkOrder(workOrderId ?? null)

  useEffect(() => {
    setActiveTab('resumen')
  }, [workOrderId])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-400">Cargando…</p>
      </div>
    )
  }

  if (!workOrder) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-400">Obra no encontrada.</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-5">
      <WorkOrderDetail workOrder={workOrder} />
    </div>
  )
}

export function WorkOrdersPage() {
  const [showNewModal, setShowNewModal] = useState(false)
  const navigate = useNavigate()
  const {
    searchQuery,
    statusFilter,
    setSearchQuery,
    setStatusFilter,
  } = useWorkOrderStore()

  const debouncedQuery = useDebounce(searchQuery, 300)

  const { data: listData, isLoading } = useWorkOrders({
    q: debouncedQuery || undefined,
    status: statusFilter ?? undefined,
    limit: 100,
  })

  const detailMatch = useMatch('/obras/:workOrderId')
  const isDetailSelected = !!detailMatch

  return (
    <div className="flex h-full gap-0">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex shrink-0 flex-col border-r border-gray-100 bg-white',
          isDetailSelected
            ? 'hidden lg:flex lg:w-80'
            : 'flex w-full lg:w-80',
        )}
      >
        {/* Search + filters */}
        <div className="border-b border-gray-100 p-3 space-y-2">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Buscar obras…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-200 py-2 pl-8 pr-3 text-sm focus:border-blue-400 focus:outline-none"
            />
          </div>
          <select
            value={statusFilter ?? ''}
            onChange={(e) =>
              setStatusFilter((e.target.value as WorkOrderStatus) || null)
            }
            className="w-full rounded-lg border border-gray-200 py-2 px-3 text-sm focus:border-blue-400 focus:outline-none"
          >
            {STATUS_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Count */}
        <div className="border-b border-gray-50 px-4 py-2">
          <p className="text-xs text-gray-400">
            {listData?.total ?? 0} obra{(listData?.total ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-gray-400">
              Cargando…
            </div>
          ) : (
            <WorkOrderList orders={listData?.items ?? []} />
          )}
        </div>

        <div className="border-t border-gray-100 p-3">
          <button
            onClick={() => setShowNewModal(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus size={14} />
            Nueva obra
          </button>
        </div>
      </div>

      {/* Right panel — detail via nested routes */}
      <div
        className={cn(
          'flex-1 overflow-hidden',
          !isDetailSelected && 'hidden lg:block',
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center bg-gray-50">
                <p className="text-gray-400">
                  Selecciona una obra para ver los detalles
                </p>
              </div>
            }
          />
          <Route path=":workOrderId" element={<WorkOrderDetailRoute />} />
        </Routes>
      </div>

      {showNewModal && (
        <NewWorkOrderModal
          onClose={() => setShowNewModal(false)}
          onCreated={(id) => {
            setShowNewModal(false)
            navigate(`/obras/${id}`)
          }}
        />
      )}
    </div>
  )
}
