import { useState } from 'react'
import dayjs from 'dayjs'
import {
  TrendingUp,
  Euro,
  Hammer,
  FileText,
  AlertCircle,
  Clock,
  CheckCircle,
  ShoppingCart,
} from 'lucide-react'
import { useDashboardSummary } from '../hooks/use-dashboard'
import { DateRangeFilter } from './DateRangeFilter'
import { KpiCard } from './KpiCard'
import { StatusBreakdown } from './StatusBreakdown'
import { MonthlyRevenueChart } from './MonthlyRevenueChart'
import { AlertsBanner } from './AlertsBanner'
import { TopCustomersTable } from './TopCustomersTable'
import { RecentActivityFeed } from './RecentActivityFeed'
import type { DateRange } from '../types'

function formatEur(value: number) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPct(value: number) {
  return `${value.toFixed(1)}%`
}

const today = dayjs()

export function DashboardPage() {
  const [dateRange, setDateRange] = useState<DateRange>({
    from: today.startOf('year').format('YYYY-MM-DD'),
    to: today.format('YYYY-MM-DD'),
  })

  const { data, isLoading, isError } = useDashboardSummary(dateRange.from, dateRange.to)

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto p-6 space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-400 mt-0.5">Resumen de actividad del negocio</p>
          </div>
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
        </div>

        {/* Alerts banner — shown as soon as data is available */}
        {data && (
          <AlertsBanner
            overdueInvoicesCount={data.overdue_invoices.length}
            pendingBudgetsOver15Days={
              data.pending_budgets.filter((b) => b.days_since_sent >= 15).length
            }
            lowStockItemsCount={data.low_stock_items_count}
          />
        )}

        {isError && (
          <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
            Error al cargar los datos del dashboard.
          </div>
        )}

        {isLoading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-white border border-gray-100 animate-pulse" />
            ))}
          </div>
        )}

        {data && (
          <>
            {/* ── Row 1: KPIs de facturación ──────────────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                title="Facturación total"
                value={formatEur(data.invoices.total_invoiced)}
                subtitle={`${data.invoices.total} facturas emitidas`}
                icon={<Euro size={16} />}
                variant="default"
              />
              <KpiCard
                title="Cobros pendientes"
                value={formatEur(data.invoices.total_pending)}
                subtitle={
                  data.invoices.overdue_count > 0
                    ? `${data.invoices.overdue_count} venció (${formatEur(data.invoices.overdue_amount)})`
                    : 'Sin facturas vencidas'
                }
                icon={<AlertCircle size={16} />}
                variant={data.invoices.overdue_count > 0 ? 'danger' : 'default'}
              />
              <KpiCard
                title="Cobrado"
                value={formatEur(data.invoices.total_collected)}
                subtitle={
                  data.invoices.avg_collection_days != null
                    ? `Promedio ${data.invoices.avg_collection_days}d de cobro`
                    : undefined
                }
                icon={<CheckCircle size={16} />}
                variant="success"
              />
              <KpiCard
                title="Tasa de cobro"
                value={
                  data.invoices.total_invoiced > 0
                    ? formatPct((data.invoices.total_collected / data.invoices.total_invoiced) * 100)
                    : '—'
                }
                subtitle="Cobrado / Facturado"
                icon={<TrendingUp size={16} />}
                variant={
                  data.invoices.total_invoiced > 0 &&
                  data.invoices.total_collected / data.invoices.total_invoiced >= 0.8
                    ? 'success'
                    : 'warning'
                }
              />
            </div>

            {/* ── Row 2: KPIs de presupuestos y obras ──────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                title="Presupuestos enviados"
                value={data.budgets.accepted + data.budgets.rejected + data.budgets.sent + data.budgets.expired}
                subtitle={`${data.budgets.total} totales (incl. borrador)`}
                icon={<FileText size={16} />}
              />
              <KpiCard
                title="Tasa de conversión"
                value={formatPct(data.budgets.conversion_rate)}
                subtitle={`${data.budgets.accepted} aceptados · ${data.budgets.rejected} rechazados`}
                icon={<TrendingUp size={16} />}
                variant={
                  data.budgets.conversion_rate >= 60
                    ? 'success'
                    : data.budgets.conversion_rate >= 40
                    ? 'warning'
                    : 'danger'
                }
              />
              <KpiCard
                title="Obras activas"
                value={data.work_orders.active_count}
                subtitle={`${data.work_orders.total} totales en el período`}
                icon={<Hammer size={16} />}
                variant={data.work_orders.active_count > 0 ? 'default' : 'success'}
              />
              <KpiCard
                title="Pedidos de compra"
                value={data.purchase_orders.total}
                subtitle={`${data.purchase_orders.pending} pendientes · ${data.purchase_orders.received} recibidos`}
                icon={<ShoppingCart size={16} />}
                variant={data.purchase_orders.pending > 0 ? 'warning' : 'default'}
              />
            </div>

            {/* ── Row 3: Gráfica principal + estados ───────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Monthly revenue chart */}
              <div className="lg:col-span-2 rounded-xl border border-gray-100 bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Facturación mensual
                </h3>
                <MonthlyRevenueChart data={data.monthly_revenue} />
              </div>

              {/* Budget stats */}
              <div className="space-y-4">
                <StatusBreakdown
                  title="Presupuestos"
                  total={data.budgets.total}
                  segments={[
                    { label: 'Borrador', value: data.budgets.draft, color: '#d1d5db' },
                    { label: 'Enviado', value: data.budgets.sent, color: '#60a5fa' },
                    { label: 'Aceptado', value: data.budgets.accepted, color: '#34d399' },
                    { label: 'Rechazado', value: data.budgets.rejected, color: '#f87171' },
                    { label: 'Caducado', value: data.budgets.expired, color: '#fbbf24' },
                  ]}
                />
                <StatusBreakdown
                  title="Obras"
                  total={data.work_orders.total}
                  segments={[
                    { label: 'Borrador', value: data.work_orders.draft, color: '#d1d5db' },
                    { label: 'Activa', value: data.work_orders.active, color: '#60a5fa' },
                    { label: 'Pend. cierre', value: data.work_orders.pending_closure, color: '#fbbf24' },
                    { label: 'Cerrada', value: data.work_orders.closed, color: '#34d399' },
                    { label: 'Cancelada', value: data.work_orders.cancelled, color: '#d1d5db' },
                  ]}
                />
              </div>
            </div>

            {/* ── Row 4: Facturas + Visitas + Pedidos ──────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatusBreakdown
                title="Facturas"
                total={data.invoices.total}
                segments={[
                  { label: 'Borrador', value: data.invoices.draft, color: '#d1d5db' },
                  { label: 'Enviada', value: data.invoices.sent, color: '#60a5fa' },
                  { label: 'Vencida', value: data.invoices.overdue_count, color: '#f87171' },
                  { label: 'Cobrada', value: data.invoices.paid, color: '#34d399' },
                  { label: 'Anulada', value: data.invoices.cancelled, color: '#9ca3af' },
                ]}
              />
              <StatusBreakdown
                title="Visitas técnicas"
                total={data.site_visits.total}
                segments={[
                  { label: 'Programada', value: data.site_visits.scheduled, color: '#60a5fa' },
                  { label: 'En curso', value: data.site_visits.in_progress, color: '#fbbf24' },
                  { label: 'Completada', value: data.site_visits.completed, color: '#34d399' },
                  { label: 'Cancelada', value: data.site_visits.cancelled, color: '#d1d5db' },
                  { label: 'No presentado', value: data.site_visits.no_show, color: '#f87171' },
                ]}
              />
              <StatusBreakdown
                title="Pedidos de compra"
                total={data.purchase_orders.total}
                segments={[
                  { label: 'Pendiente', value: data.purchase_orders.pending, color: '#fbbf24' },
                  { label: 'Recibido', value: data.purchase_orders.received, color: '#34d399' },
                  { label: 'Cancelado', value: data.purchase_orders.cancelled, color: '#d1d5db' },
                ]}
              />
            </div>

            {/* ── Row 5: Top clientes + Actividad reciente ─────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TopCustomersTable customers={data.top_customers} />
              <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100">
                  <h3 className="text-sm font-semibold text-gray-700">Actividad reciente</h3>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  <RecentActivityFeed items={data.recent_activity} />
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
