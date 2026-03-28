interface BudgetStatusBadgeProps {
  status: string
}

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  draft:    { label: 'Borrador',  className: 'bg-gray-100 text-gray-600' },
  sent:     { label: 'Enviado',   className: 'bg-blue-100 text-blue-700' },
  accepted: { label: 'Aceptado', className: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rechazado', className: 'bg-red-100 text-red-700' },
  expired:  { label: 'Expirado', className: 'bg-amber-100 text-amber-700' },
}

export function BudgetStatusBadge({ status }: BudgetStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  )
}
