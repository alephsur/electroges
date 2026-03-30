import { useState } from 'react'
import { FileText, Plus, Search } from 'lucide-react'
import { useBudgetStore } from '../store/budget-store'
import { useBudget, useBudgets } from '../hooks/use-budgets'
import { BudgetList } from './BudgetList'
import { BudgetDetail } from './BudgetDetail'
import { BudgetForm } from './BudgetForm'
import { BudgetFromVisitForm } from './BudgetFromVisitForm'
import type { BudgetStatus } from '../types'

const STATUS_OPTIONS: { value: BudgetStatus; label: string }[] = [
  { value: 'draft', label: 'Borrador' },
  { value: 'sent', label: 'Enviado' },
  { value: 'accepted', label: 'Aceptado' },
  { value: 'rejected', label: 'Rechazado' },
  { value: 'expired', label: 'Expirado' },
]

type NewBudgetMode = 'direct' | 'from-visit' | null

export function BudgetsPage() {
  const [newBudgetMode, setNewBudgetMode] = useState<NewBudgetMode>(null)
  const [showModeSelector, setShowModeSelector] = useState(false)
  const {
    searchQuery,
    statusFilter,
    selectedBudgetId,
    showAllVersions,
    setSearchQuery,
    setStatusFilter,
    setShowAllVersions,
  } = useBudgetStore()

  const { data, isLoading } = useBudgets({
    q: searchQuery || undefined,
    status: statusFilter ?? undefined,
    latest_only: !showAllVersions,
    limit: 200,
  })

  const { data: selectedBudget } = useBudget(selectedBudgetId)

  const budgets = data?.items ?? []

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel */}
      <div
        className={`flex flex-col border-r border-gray-100 ${
          selectedBudgetId ? 'w-[45%]' : 'flex-1'
        } min-w-0`}
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
            <div className="relative">
              <button
                onClick={() => setShowModeSelector(!showModeSelector)}
                className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus size={15} />
                Nuevo presupuesto
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
      </div>

      {/* Right panel: detail */}
      {selectedBudgetId && (
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {selectedBudget ? (
            <BudgetDetail budget={selectedBudget} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              Cargando...
            </div>
          )}
        </div>
      )}

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
