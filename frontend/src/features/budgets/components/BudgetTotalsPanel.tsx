import type { Budget } from '../types'
import { BudgetMarginIndicator } from './BudgetMarginIndicator'

interface BudgetTotalsPanelProps {
  budget: Budget
}

function formatEur(value: number) {
  return (
    value.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + ' €'
  )
}

export function BudgetTotalsPanel({ budget }: BudgetTotalsPanelProps) {
  const { totals } = budget

  const sectionsById = new Map(budget.sections.map((s) => [s.id, s]))
  const sectionRows = totals.sections
    .filter((row) => row.lines_count > 0)
    .map((row) => {
      if (row.section_id === null) {
        return { key: '__none__', name: 'Sin capítulo', row }
      }
      const sec = sectionsById.get(row.section_id)
      return {
        key: row.section_id,
        name: sec?.name ?? 'Capítulo',
        row,
      }
    })
  const hasSections = sectionRows.length > 1 || budget.sections.length > 0

  return (
    <div className="space-y-4">
      {/* Per-section breakdown */}
      {hasSections && sectionRows.length > 0 && (
        <div className="rounded-lg border border-gray-200">
          <div className="px-4 py-2 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Desglose por capítulo
          </div>
          <div className="divide-y divide-gray-100">
            {sectionRows.map(({ key, name, row }) => (
              <div
                key={key}
                className="flex items-center justify-between px-4 py-2 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="text-gray-700">{name}</span>
                  <span className="text-xs text-gray-400">
                    ({row.lines_count}{' '}
                    {row.lines_count === 1 ? 'línea' : 'líneas'})
                  </span>
                </div>
                <span className="font-medium text-gray-900">
                  {formatEur(row.subtotal)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Public totals */}
      <div className="rounded-lg border border-gray-200 divide-y divide-gray-100">
        <div className="flex justify-between px-4 py-2.5 text-sm">
          <span className="text-gray-600">Subtotal</span>
          <span className="font-medium">
            {formatEur(totals.subtotal_before_discount)}
          </span>
        </div>
        {budget.discount_pct > 0 && (
          <div className="flex justify-between px-4 py-2.5 text-sm">
            <span className="text-red-600">
              Descuento ({budget.discount_pct}%)
            </span>
            <span className="text-red-600 font-medium">
              -{formatEur(totals.discount_amount)}
            </span>
          </div>
        )}
        <div className="flex justify-between px-4 py-2.5 text-sm">
          <span className="text-gray-600">Base imponible</span>
          <span className="font-medium">{formatEur(totals.taxable_base)}</span>
        </div>
        <div className="flex justify-between px-4 py-2.5 text-sm">
          <span className="text-gray-600">IVA ({budget.tax_rate}%)</span>
          <span className="font-medium">{formatEur(totals.tax_amount)}</span>
        </div>
        <div className="flex justify-between px-4 py-3 bg-gray-50">
          <span className="text-base font-bold text-gray-900">TOTAL</span>
          <span className="text-base font-bold text-gray-900">
            {formatEur(totals.total)}
          </span>
        </div>
      </div>

      {/* Internal margin section */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Margen interno
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Coste estimado</span>
          <span className="font-medium">{formatEur(totals.total_cost)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Margen bruto</span>
          <span className="font-medium">{formatEur(totals.gross_margin)}</span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">Margen %</span>
          <BudgetMarginIndicator
            marginPct={totals.gross_margin_pct}
            marginStatus={totals.margin_status}
            size="md"
          />
        </div>
      </div>
    </div>
  )
}
