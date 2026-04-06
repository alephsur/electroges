import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams, useNavigate } from 'react-router-dom'
import { HardHat, Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { useWorkOrder, useWorkOrders } from '../hooks/use-work-orders'
import { useWorkOrderStore, PAGE_SIZE_OPTIONS } from '../store/work-order-store'
import type { PageSize } from '../store/work-order-store'
import { WorkOrderList } from './WorkOrderList'
import { WorkOrderDetail } from './WorkOrderDetail'
import { NewWorkOrderModal } from './NewWorkOrderModal'
import type { WorkOrderStatus } from '../types'

const STATUS_OPTIONS: { value: WorkOrderStatus; label: string }[] = [
  { value: 'draft', label: 'Borrador' },
  { value: 'active', label: 'En ejecución' },
  { value: 'pending_closure', label: 'Pdte. cierre' },
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
    page,
    pageSize,
    setSearchQuery,
    setStatusFilter,
    setPage,
    setPageSize,
  } = useWorkOrderStore()

  const debouncedQuery = useDebounce(searchQuery, 300)

  const { data: listData, isLoading } = useWorkOrders({
    q: debouncedQuery || undefined,
    status: statusFilter ?? undefined,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  const totalPages = listData ? Math.ceil(listData.total / pageSize) : 1
  const detailMatch = useMatch('/obras/:workOrderId')
  const isDetailSelected = !!detailMatch

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex flex-col border-r border-gray-100 min-w-0',
          isDetailSelected
            ? 'hidden lg:flex lg:w-[42%] lg:shrink-0'
            : 'flex flex-1',
        )}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardHat size={18} className="text-gray-600" />
              <h1 className="text-lg font-semibold text-gray-900">Obras</h1>
              {listData && (
                <span className="text-sm text-gray-400">({listData.total})</span>
              )}
            </div>
            <button
              onClick={() => setShowNewModal(true)}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus size={15} />
              <span className="hidden sm:inline">Nueva obra</span>
              <span className="sm:hidden">Nueva</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Buscar obras…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status filter pills */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setStatusFilter(null)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                statusFilter === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Todas
            </button>
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() =>
                  setStatusFilter(opt.value === statusFilter ? null : opt.value)
                }
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                  statusFilter === opt.value
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-gray-400">Cargando…</div>
          ) : (
            <WorkOrderList orders={listData?.items ?? []} />
          )}
        </div>

        {/* Pagination */}
        {!isLoading && listData && listData.total > 0 && (
          <div className="shrink-0 border-t border-gray-100 px-4 py-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span>Por página:</span>
              {PAGE_SIZE_OPTIONS.map((size) => (
                <button
                  key={size}
                  onClick={() => setPageSize(size as PageSize)}
                  className={`rounded px-2 py-0.5 font-medium transition-colors ${
                    pageSize === size
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, listData.total)} de {listData.total}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ›
                </button>
              </div>
            </div>
          </div>
        )}
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
                <p className="text-sm text-gray-400">
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
