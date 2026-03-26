import { useEffect, useState } from 'react'
import { ArrowDownCircle, ArrowUpCircle, SlidersHorizontal } from 'lucide-react'
import { useItemMovements } from '../hooks/use-stock-movements'
import type { StockMovement } from '../types'

interface MovementHistoryProps {
  itemId: string
  unit: string
}

const PAGE_SIZE = 20

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 60) return `hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `hace ${hours} h`
  const days = Math.floor(hours / 24)
  return `hace ${days} día${days !== 1 ? 's' : ''}`
}

function MovementRow({ m, unit }: { m: StockMovement; unit: string }) {
  const isEntry = m.movement_type === 'entry'
  const isAdjustment = m.reference_type === 'manual_adjustment'
  const total = Number(m.quantity) * Number(m.unit_cost)

  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
      <div className="mt-0.5 shrink-0">
        {isAdjustment ? (
          <SlidersHorizontal size={18} className="text-gray-400" />
        ) : isEntry ? (
          <ArrowUpCircle size={18} className="text-green-500" />
        ) : (
          <ArrowDownCircle size={18} className="text-red-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span
            className={
              isEntry ? 'text-sm font-semibold text-green-700' : 'text-sm font-semibold text-red-600'
            }
          >
            {isEntry ? '+' : '-'}
            {Number(m.quantity).toLocaleString('es-ES', { maximumFractionDigits: 3 })} {unit}
          </span>
          <span className="text-xs text-gray-400 shrink-0">{relativeTime(m.created_at)}</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">
          {Number(m.unit_cost).toLocaleString('es-ES', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 4,
          })}{' '}
          / {unit} · Total{' '}
          {total.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {m.reference_type === 'purchase_order'
            ? 'Pedido a proveedor'
            : m.reference_type === 'work_order'
              ? 'Obra'
              : 'Ajuste manual'}
          {m.notes && ` · ${m.notes}`}
        </p>
      </div>
    </div>
  )
}

export function MovementHistory({ itemId, unit }: MovementHistoryProps) {
  const [page, setPage] = useState(0)
  const [allMovements, setAllMovements] = useState<StockMovement[]>([])

  // Reset when item changes
  useEffect(() => {
    setPage(0)
    setAllMovements([])
  }, [itemId])

  const { data: pageData, isFetching } = useItemMovements(itemId, page * PAGE_SIZE, PAGE_SIZE)

  // Accumulate pages into allMovements
  useEffect(() => {
    if (!pageData || pageData.length === 0) return
    setAllMovements((prev) => {
      const knownIds = new Set(prev.map((m) => m.id))
      const newOnes = pageData.filter((m) => !knownIds.has(m.id))
      return newOnes.length > 0 ? [...prev, ...newOnes] : prev
    })
  }, [pageData])

  const hasMore = pageData !== undefined && pageData.length === PAGE_SIZE

  if (allMovements.length === 0 && !isFetching) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        Este material no tiene movimientos de stock registrados
      </p>
    )
  }

  return (
    <div>
      <div className="divide-y divide-gray-50">
        {allMovements.map((m) => (
          <MovementRow key={m.id} m={m} unit={unit} />
        ))}
      </div>
      {isFetching && (
        <p className="text-center text-xs text-gray-400 py-3">Cargando...</p>
      )}
      {hasMore && !isFetching && (
        <button
          onClick={() => setPage((p) => p + 1)}
          className="mt-3 w-full py-2 text-sm text-brand-600 hover:text-brand-800 font-medium border border-brand-100 rounded-lg hover:bg-brand-50 transition-colors"
        >
          Cargar más
        </button>
      )}
    </div>
  )
}
