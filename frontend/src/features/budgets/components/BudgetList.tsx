import { FileText, GitBranch } from 'lucide-react'
import { useNavigate, useMatch } from 'react-router-dom'
import type { BudgetSummary } from '../types'
import { useBudgetStore } from '../store/budget-store'
import { BudgetStatusBadge } from './BudgetStatusBadge'
import { BudgetMarginIndicator } from './BudgetMarginIndicator'

interface BudgetListProps {
  budgets: BudgetSummary[]
  isLoading?: boolean
}

export function BudgetList({ budgets, isLoading }: BudgetListProps) {
  const navigate = useNavigate()
  const match = useMatch('/presupuestos/:budgetId')
  const selectedBudgetId = match?.params.budgetId ?? null
  const { showAllVersions } = useBudgetStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-gray-400">
        Cargando presupuestos...
      </div>
    )
  }

  if (budgets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-gray-400">
        <FileText size={36} className="mb-3 text-gray-300" />
        <p className="font-medium text-gray-500">Sin presupuestos</p>
        <p className="mt-1 text-sm">Crea un nuevo presupuesto para empezar</p>
      </div>
    )
  }

  const visibleBudgets = showAllVersions
    ? budgets
    : budgets.filter((b) => b.is_latest_version)

  return (
    <div className="divide-y divide-gray-100">
      {visibleBudgets.map((budget) => (
        <div
          key={budget.id}
          onClick={() => navigate(`/presupuestos/${budget.id}`)}
          className={`cursor-pointer p-4 transition-colors hover:bg-gray-50 ${
            selectedBudgetId === budget.id
              ? 'border-l-2 border-blue-600 bg-blue-50'
              : ''
          } ${!budget.is_latest_version ? 'ml-4 bg-gray-50/50' : ''}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-gray-900 truncate">
                  {budget.budget_number}
                </span>
                {budget.version > 1 && (
                  <span className="flex items-center gap-0.5 text-xs text-gray-400">
                    <GitBranch size={11} />
                    v{budget.version}
                  </span>
                )}
                <BudgetStatusBadge status={budget.effective_status} />
              </div>

              <div className="text-xs text-gray-600 mb-1">
                {budget.customer_name ?? <span className="italic text-gray-400">Sin cliente</span>}
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>
                  {new Date(budget.issue_date).toLocaleDateString('es-ES', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
                <BudgetMarginIndicator
                  marginPct={budget.gross_margin_pct}
                  marginStatus={budget.margin_status}
                />
              </div>
            </div>

            <div className="shrink-0 text-right">
              <div className="text-sm font-bold text-gray-900">
                {Number(budget.total).toLocaleString('es-ES', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{' '}
                €
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {budget.lines_count} líneas
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
