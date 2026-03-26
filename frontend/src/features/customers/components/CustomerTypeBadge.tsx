import type { CustomerType } from '../types'

const CONFIG: Record<CustomerType, { label: string; className: string }> = {
  individual: {
    label: 'Particular',
    className: 'bg-gray-100 text-gray-600',
  },
  company: {
    label: 'Empresa',
    className: 'bg-blue-100 text-blue-700',
  },
  community: {
    label: 'Comunidad',
    className: 'bg-green-100 text-green-700',
  },
}

interface CustomerTypeBadgeProps {
  type: CustomerType
  size?: 'sm' | 'md'
}

export function CustomerTypeBadge({ type, size = 'sm' }: CustomerTypeBadgeProps) {
  const config = CONFIG[type] ?? CONFIG.individual
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'

  return (
    <span className={`inline-flex items-center rounded-full font-medium ${sizeClass} ${config.className}`}>
      {config.label}
    </span>
  )
}
