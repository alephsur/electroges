import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import type { CashFlowBucket } from '../types'

interface Props {
  buckets: CashFlowBucket[]
}

const BUCKET_COLORS: Record<string, string> = {
  '0_30':    '#34d399',
  '31_60':   '#60a5fa',
  '61_90':   '#fbbf24',
  '91_plus': '#f87171',
}

function formatEur(value: number) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const bucket = payload[0]
  return (
    <div className="rounded-lg border border-gray-100 bg-white p-3 shadow-lg text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      <p style={{ color: bucket.fill }}>
        {formatEur(bucket.value)}
      </p>
      <p className="text-gray-400 mt-0.5">{bucket.payload.invoice_count} factura(s)</p>
    </div>
  )
}

export function CashFlowChart({ buckets }: Props) {
  const total = buckets.reduce((sum, b) => sum + b.amount, 0)
  const hasData = buckets.some((b) => b.amount > 0)

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">Cash-flow previsto</h3>
          <p className="text-xs text-gray-400 mt-0.5">Facturas pendientes por vencimiento</p>
        </div>
        {total > 0 && (
          <div className="text-right">
            <p className="text-sm font-bold text-gray-800">{formatEur(total)}</p>
            <p className="text-xs text-gray-400">total pendiente</p>
          </div>
        )}
      </div>

      <div className="p-4">
        {!hasData ? (
          <div className="flex items-center justify-center h-40 text-sm text-gray-400">
            Sin cobros pendientes
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart
                data={buckets}
                margin={{ top: 4, right: 4, left: 4, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 11, fill: '#9ca3af' }}
                  axisLine={false}
                  tickLine={false}
                  width={36}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f9fafb' }} />
                <Bar dataKey="amount" name="Pendiente" radius={[4, 4, 0, 0]} maxBarSize={56}>
                  {buckets.map((entry) => (
                    <Cell key={entry.bucket} fill={BUCKET_COLORS[entry.bucket] ?? '#9ca3af'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <div className="mt-3 grid grid-cols-4 gap-2">
              {buckets.map((b) => (
                <div key={b.bucket} className="text-center">
                  <div
                    className="w-2 h-2 rounded-full mx-auto mb-1"
                    style={{ backgroundColor: BUCKET_COLORS[b.bucket] ?? '#9ca3af' }}
                  />
                  <p className="text-xs text-gray-500">{b.label}</p>
                  <p className="text-xs font-semibold text-gray-700">{formatEur(b.amount)}</p>
                  <p className="text-xs text-gray-400">{b.invoice_count} fact.</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
