import { useBudgetStore } from '../store/budget-store'
import { useBudgetVersions } from '../hooks/use-budgets'
import { BudgetStatusBadge } from './BudgetStatusBadge'

interface BudgetVersionHistoryProps {
  budgetId: string
}

export function BudgetVersionHistory({ budgetId }: BudgetVersionHistoryProps) {
  const { data: versions, isLoading } = useBudgetVersions(budgetId)
  const { setSelectedBudgetId } = useBudgetStore()

  if (isLoading) {
    return (
      <div className="py-4 text-center text-sm text-gray-400">Cargando versiones...</div>
    )
  }

  if (!versions || versions.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-gray-400">
        Sin historial de versiones.
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {versions.map((v) => (
        <div
          key={v.id}
          onClick={() => setSelectedBudgetId(v.id)}
          className={`flex cursor-pointer items-center justify-between rounded-md border px-3 py-2.5 transition-colors hover:bg-gray-50 ${
            v.id === budgetId
              ? 'border-blue-200 bg-blue-50'
              : 'border-gray-100'
          } ${!v.is_latest_version ? 'opacity-60' : ''}`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">v{v.version}</span>
            <span className="text-sm text-gray-700">{v.budget_number}</span>
            {!v.is_latest_version && (
              <span className="text-xs text-gray-400">(anterior)</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">
              {new Date(v.issue_date).toLocaleDateString('es-ES')}
            </span>
            <span className="text-sm font-medium text-gray-900">
              {v.total.toLocaleString('es-ES', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              €
            </span>
            <BudgetStatusBadge status={v.effective_status} />
          </div>
        </div>
      ))}
    </div>
  )
}
