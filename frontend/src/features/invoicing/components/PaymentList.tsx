import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useDeletePayment } from '../hooks/use-payments'
import type { Payment } from '../types'

const METHOD_LABEL: Record<string, string> = {
  transfer: 'Transferencia',
  cash: 'Efectivo',
  card: 'Tarjeta',
  direct_debit: 'Domiciliación',
}

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('es-ES')
}

interface Props {
  invoiceId: string
  payments: Payment[]
  canDelete: boolean
}

export function PaymentList({ invoiceId, payments, canDelete }: Props) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { mutate: deletePayment } = useDeletePayment(invoiceId)

  if (payments.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-gray-400">
        No hay cobros registrados
      </p>
    )
  }

  return (
    <div className="divide-y divide-gray-100">
      {payments.map((p) => (
        <div
          key={p.id}
          className="flex items-center justify-between py-3"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-800">
                {fmt(p.amount)} €
              </span>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                {METHOD_LABEL[p.method] ?? p.method}
              </span>
            </div>
            <div className="mt-0.5 text-xs text-gray-500">
              {fmtDate(p.payment_date)}
              {p.reference && ` · Ref: ${p.reference}`}
            </div>
          </div>
          {canDelete && (
            <button
              onClick={() => {
                setDeletingId(p.id)
                deletePayment(p.id, {
                  onSettled: () => setDeletingId(null),
                })
              }}
              disabled={deletingId === p.id}
              className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-40"
              title="Eliminar pago"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
