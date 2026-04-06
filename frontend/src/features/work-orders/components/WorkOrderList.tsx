import { useNavigate, useMatch } from 'react-router-dom'
import { WorkOrderStatusBadge } from './WorkOrderStatusBadge'
import type { WorkOrderSummary } from '../types'

function fmt(n: number) {
  return n.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

interface WorkOrderListProps {
  orders: WorkOrderSummary[]
}

export function WorkOrderList({ orders }: WorkOrderListProps) {
  const navigate = useNavigate()
  const match = useMatch('/obras/:workOrderId')
  const selectedId = match?.params.workOrderId ?? null

  if (orders.length === 0) {
    return (
      <div className="py-16 text-center text-sm text-gray-400">
        No se encontraron obras.
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-50">
      {orders.map((order) => {
        const isSelected = order.id === selectedId
        const pct = Math.min(order.progress_pct, 100)

        return (
          <button
            key={order.id}
            onClick={() => navigate(`/obras/${order.id}`)}
            className={`block w-full px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
              isSelected ? 'bg-blue-50' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-gray-900">
                    {order.work_order_number}
                  </span>
                  <WorkOrderStatusBadge status={order.status} />
                </div>
                <p className="mt-0.5 truncate text-sm text-gray-600">
                  {order.customer_name}
                </p>
                {order.address && (
                  <p className="mt-0.5 truncate text-xs text-gray-400">
                    {order.address}
                  </p>
                )}
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-medium text-gray-900">
                  {fmt(order.budget_total)}€
                </p>
                <p className="text-xs text-gray-500">
                  {fmt(order.actual_cost)}€ real
                </p>
              </div>
            </div>

            {/* Mini progress bar */}
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-blue-400 transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="shrink-0 text-xs text-gray-400">
                  {order.completed_tasks}/{order.total_tasks}
                </span>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
