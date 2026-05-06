import { useState, useEffect } from 'react'
import { Routes, Route, useMatch, useNavigate, useParams } from 'react-router-dom'
import { FileText, LayoutTemplate, Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useBudgetStore, PAGE_SIZE_OPTIONS } from '../store/budget-store'
import type { PageSize } from '../store/budget-store'
import { useBudget, useBudgets } from '../hooks/use-budgets'
import { BudgetList } from './BudgetList'
import { BudgetDetail } from './BudgetDetail'
import { BudgetForm } from './BudgetForm'
import { BudgetFromVisitForm } from './BudgetFromVisitForm'
import { TemplatesManager } from './TemplatesManager'
import type { BudgetStatus } from '../types'

const STATUS_OPTIONS: { value: BudgetStatus; label: string }[] = [
  { value: 'draft', label: 'Borrador' },
  { value: 'sent', label: 'Enviado' },
  { value: 'accepted', label: 'Aceptado' },
  { value: 'rejected', label: 'Rechazado' },
  { value: 'expired', label: 'Expirado' },
]

type NewBudgetMode = 'direct' | 'from-visit' | null

function BudgetDetailRoute() {
  const { budgetId } = useParams<{ budgetId: string }>()
  const { data: budget } = useBudget(budgetId ?? null)
  const { setActiveTab, setShowAddLineForm } = useBudgetStore()

  useEffect(() => {
    setActiveTab('lineas')
    setShowAddLineForm(false)
  }, [budgetId])

  if (!budget) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gray-400">
        Cargando...
      </div>
    )
  }

  return <BudgetDetail budget={budget} />
}

export function BudgetsPage() {
  const navigate = useNavigate()
  const [newBudgetMode, setNewBudgetMode] = useState<NewBudgetMode>(null)
  const [showModeSelector, setShowModeSelector] = useState(false)
  const {
    searchQuery,
    statusFilter,
    showAllVersions,
    page,
    pageSize,
    setSearchQuery,
    setStatusFilter,
    setShowAllVersions,
    setPage,
    setPageSize,
  } = useBudgetStore()

  const templatesMatch = useMatch('/presupuestos/plantillas')
  const detailMatch = useMatch('/presupuestos/:budgetId')
  const isTemplatesView = !!templatesMatch
  const isDetailSelected = !isTemplatesView && !!detailMatch

  const { data, isLoading } = useBudgets({
    q: searchQuery || undefined,
    status: statusFilter ?? undefined,
    latest_only: !showAllVersions,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  if (isTemplatesView) {
    return <TemplatesManager />
  }

  const budgets = data?.items ?? []
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

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
              <FileText size={18} className="text-gray-600" />
              <h1 className="text-lg font-semibold text-gray-900">Presupuestos</h1>
              {data && (
                <span className="text-sm text-gray-400">({data.total})</span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => navigate('/presupuestos/plantillas')}
                title="Plantillas"
                className="flex items-center gap-1.5 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
              >
                <LayoutTemplate size={14} />
                <span className="hidden sm:inline">Plantillas</span>
              </button>
              <div className="relative">
              <button
                onClick={() => setShowModeSelector(!showModeSelector)}
                className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus size={15} />
                <span className="hidden sm:inline">Nuevo presupuesto</span>
                <span className="sm:hidden">Nuevo</span>
              </button>
              {showModeSelector && (
                <div className="absolute right-0 top-full mt-1 z-10 w-52 rounded-lg border border-gray-100 bg-white shadow-lg py-1">
                  <button
                    onClick={() => {
                      setNewBudgetMode('from-visit')
                      setShowModeSelector(false)
                    }}
                    className="w-full px-4 py-2.5 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Desde una visita técnica
                  </button>
                  <button
                    onClick={() => {
                      setNewBudgetMode('direct')
                      setShowModeSelector(false)
                    }}
                    className="w-full px-4 py-2.5 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Presupuesto independiente
                  </button>
                </div>
              )}
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por número, cliente..."
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status filter pills */}
          <div className="flex flex-wrap gap-1.5 mb-2">
            <button
              onClick={() => setStatusFilter(null)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                statusFilter === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Todos
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

          {/* Show all versions toggle */}
          <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
            <input
              type="checkbox"
              checked={showAllVersions}
              onChange={(e) => setShowAllVersions(e.target.checked)}
              className="rounded"
            />
            Mostrar versiones anteriores
          </label>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          <BudgetList budgets={budgets} isLoading={isLoading} />
        </div>

        {/* Pagination */}
        {!isLoading && data && data.total > 0 && (
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
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, data.total)} de {data.total}
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
          'flex-1 flex flex-col overflow-hidden min-w-0',
          !isDetailSelected && 'hidden lg:flex',
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center text-sm text-gray-400">
                Selecciona un presupuesto para ver el detalle
              </div>
            }
          />
          <Route path=":budgetId" element={<BudgetDetailRoute />} />
        </Routes>
      </div>

      {/* Modals */}
      {newBudgetMode === 'direct' && (
        <BudgetForm onClose={() => setNewBudgetMode(null)} />
      )}
      {newBudgetMode === 'from-visit' && (
        <BudgetFromVisitForm onClose={() => setNewBudgetMode(null)} />
      )}
    </div>
  )
}
