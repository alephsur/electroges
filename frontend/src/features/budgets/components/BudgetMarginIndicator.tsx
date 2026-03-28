import type { MarginStatus } from '../types'

interface BudgetMarginIndicatorProps {
  marginPct: number
  marginStatus: MarginStatus
  size?: 'sm' | 'md'
}

const STATUS_CONFIG: Record<
  MarginStatus,
  { dotClass: string; textClass: string }
> = {
  red:   { dotClass: 'bg-red-500',   textClass: 'text-red-600' },
  amber: { dotClass: 'bg-amber-400', textClass: 'text-amber-600' },
  green: { dotClass: 'bg-green-500', textClass: 'text-green-600' },
}

export function BudgetMarginIndicator({
  marginPct,
  marginStatus,
  size = 'sm',
}: BudgetMarginIndicatorProps) {
  const config = STATUS_CONFIG[marginStatus]
  const dotSize = size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5'
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <span
      className={`inline-flex items-center gap-1 ${textSize} font-medium ${config.textClass}`}
      title="Margen bruto estimado sobre precio de venta. Dato interno."
    >
      <span className={`inline-block rounded-full ${dotSize} ${config.dotClass}`} />
      {Number(marginPct).toFixed(1)}%
    </span>
  )
}
