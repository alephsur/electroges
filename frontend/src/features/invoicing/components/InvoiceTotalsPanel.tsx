import type { InvoiceTotals } from '../types'

interface Props {
  totals: InvoiceTotals
  tax_rate: number
  discount_pct: number
}

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

export function InvoiceTotalsPanel({ totals, tax_rate, discount_pct }: Props) {
  return (
    <div className="ml-auto w-64 space-y-1 rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Subtotal</span>
        <span>{fmt(totals.subtotal_before_discount)} €</span>
      </div>
      {totals.discount_amount > 0 && (
        <div className="flex justify-between text-sm text-red-600">
          <span>Descuento ({discount_pct}%)</span>
          <span>-{fmt(totals.discount_amount)} €</span>
        </div>
      )}
      <div className="flex justify-between text-sm text-gray-600">
        <span>Base imponible</span>
        <span>{fmt(totals.taxable_base)} €</span>
      </div>
      <div className="flex justify-between text-sm text-gray-600">
        <span>IVA ({tax_rate}%)</span>
        <span>{fmt(totals.tax_amount)} €</span>
      </div>
      <div className="mt-2 flex justify-between border-t border-gray-200 pt-2 text-base font-bold">
        <span>Total</span>
        <span>{fmt(totals.total)} €</span>
      </div>
      {totals.total_paid > 0 && (
        <div className="flex justify-between text-sm text-green-600">
          <span>Cobrado</span>
          <span>{fmt(totals.total_paid)} €</span>
        </div>
      )}
      {!totals.is_fully_paid && totals.pending_amount > 0 && (
        <div className="flex justify-between text-sm font-medium text-gray-800">
          <span>Pendiente</span>
          <span>{fmt(totals.pending_amount)} €</span>
        </div>
      )}
    </div>
  )
}
