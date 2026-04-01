import type { ReactNode } from 'react'
import { clsx } from 'clsx'

interface Props {
  title: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  trend?: { value: number; label: string }
  variant?: 'default' | 'success' | 'warning' | 'danger'
}

const variantStyles = {
  default: 'bg-white border-gray-100',
  success: 'bg-white border-green-100',
  warning: 'bg-white border-amber-100',
  danger: 'bg-white border-red-100',
}

const iconStyles = {
  default: 'bg-blue-50 text-blue-600',
  success: 'bg-green-50 text-green-600',
  warning: 'bg-amber-50 text-amber-600',
  danger: 'bg-red-50 text-red-600',
}

export function KpiCard({ title, value, subtitle, icon, variant = 'default' }: Props) {
  return (
    <div className={clsx('rounded-xl border p-4 flex gap-3 items-start', variantStyles[variant])}>
      {icon && (
        <div className={clsx('rounded-lg p-2 shrink-0', iconStyles[variant])}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-gray-500 font-medium truncate">{title}</p>
        <p className="text-2xl font-bold text-gray-900 leading-tight mt-0.5">{value}</p>
        {subtitle && (
          <p className="text-xs text-gray-400 mt-0.5 truncate">{subtitle}</p>
        )}
      </div>
    </div>
  )
}
