import { useNavigate } from 'react-router-dom'

interface AlertPill {
  label: string
  count: number
  variant: 'budget' | 'stock' | 'invoice'
  route: string
}

const pillStyles: Record<AlertPill['variant'], string> = {
  budget:  'border-yellow-600/40 text-yellow-800 bg-yellow-50 hover:bg-yellow-100',
  stock:   'border-red-400/40 text-red-700 bg-red-50 hover:bg-red-100',
  invoice: 'border-red-400/40 text-red-700 bg-red-50 hover:bg-red-100',
}

const dotStyles: Record<AlertPill['variant'], string> = {
  budget:  'bg-yellow-600',
  stock:   'bg-red-500',
  invoice: 'bg-red-500',
}

interface Props {
  overdueInvoicesCount: number
  pendingBudgetsOver15Days: number
  lowStockItemsCount: number
}

export function AlertsBanner({
  overdueInvoicesCount,
  pendingBudgetsOver15Days,
  lowStockItemsCount,
}: Props) {
  const navigate = useNavigate()

  const pills: AlertPill[] = [
    {
      label: `${pendingBudgetsOver15Days} presupuesto${pendingBudgetsOver15Days !== 1 ? 's' : ''} sin respuesta +15 días`,
      count: pendingBudgetsOver15Days,
      variant: 'budget',
      route: '/presupuestos',
    },
    {
      label: `${lowStockItemsCount} material${lowStockItemsCount !== 1 ? 'es' : ''} bajo stock mínimo`,
      count: lowStockItemsCount,
      variant: 'stock',
      route: '/inventario',
    },
    {
      label: `${overdueInvoicesCount} factura${overdueInvoicesCount !== 1 ? 's' : ''} vencida${overdueInvoicesCount !== 1 ? 's' : ''}`,
      count: overdueInvoicesCount,
      variant: 'invoice',
      route: '/facturacion',
    },
  ].filter((p) => p.count > 0) as AlertPill[]

  if (pills.length === 0) return null

  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3 flex items-center gap-4 flex-wrap">
      <span className="text-xs font-semibold tracking-widest text-gray-400 uppercase shrink-0">
        Alertas
      </span>
      <div className="flex items-center gap-2 flex-wrap">
        {pills.map((pill) => (
          <button
            key={pill.variant}
            onClick={() => navigate(pill.route)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${pillStyles[pill.variant]}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${dotStyles[pill.variant]}`} />
            {pill.label}
          </button>
        ))}
      </div>
    </div>
  )
}
