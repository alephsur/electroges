import { useState, useEffect } from 'react'
import { Settings, Bell, BellOff, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import type { DashboardSummary } from '../types'

// ── Types ──────────────────────────────────────────────────────────────────

interface AlertConfig {
  pending_budget_days: number          // alert if budget sent > N days with no reply
  overdue_invoice_min_days: number     // alert if invoice overdue > N days
  pending_closure_enabled: boolean     // alert for work orders in pending_closure
  low_stock_enabled: boolean           // alert for low stock (always computed globally)
}

interface ActiveAlert {
  id: string
  severity: 'danger' | 'warning' | 'info'
  message: string
  count: number
}

// ── Defaults & storage ─────────────────────────────────────────────────────

const STORAGE_KEY = 'electroges_alert_config'

const DEFAULT_CONFIG: AlertConfig = {
  pending_budget_days: 7,
  overdue_invoice_min_days: 0,
  pending_closure_enabled: true,
  low_stock_enabled: true,
}

function loadConfig(): AlertConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_CONFIG
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
  } catch {
    return DEFAULT_CONFIG
  }
}

function saveConfig(config: AlertConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

// ── Alert computation ──────────────────────────────────────────────────────

function computeAlerts(data: DashboardSummary, config: AlertConfig): ActiveAlert[] {
  const alerts: ActiveAlert[] = []

  // Presupuestos enviados sin respuesta > N días
  const staleBudgets = data.pending_budgets.filter(
    (b) => b.days_since_sent > config.pending_budget_days,
  )
  if (staleBudgets.length > 0) {
    alerts.push({
      id: 'pending_budgets',
      severity: staleBudgets.length >= 3 ? 'danger' : 'warning',
      message: `${staleBudgets.length} presupuesto${staleBudgets.length > 1 ? 's' : ''} enviado${staleBudgets.length > 1 ? 's' : ''} hace más de ${config.pending_budget_days} días sin respuesta`,
      count: staleBudgets.length,
    })
  }

  // Facturas vencidas > N días
  const criticalOverdue = data.overdue_invoices.filter(
    (inv) => inv.days_overdue > config.overdue_invoice_min_days,
  )
  if (criticalOverdue.length > 0) {
    alerts.push({
      id: 'overdue_invoices',
      severity: criticalOverdue.length >= 3 ? 'danger' : 'warning',
      message: `${criticalOverdue.length} factura${criticalOverdue.length > 1 ? 's' : ''} vencida${criticalOverdue.length > 1 ? 's' : ''} sin cobrar`,
      count: criticalOverdue.length,
    })
  }

  // Obras en pending_closure
  if (config.pending_closure_enabled && data.work_orders.pending_closure > 0) {
    alerts.push({
      id: 'pending_closure',
      severity: 'info',
      message: `${data.work_orders.pending_closure} obra${data.work_orders.pending_closure > 1 ? 's' : ''} lista${data.work_orders.pending_closure > 1 ? 's' : ''} para cerrar`,
      count: data.work_orders.pending_closure,
    })
  }

  // Stock bajo mínimos
  if (config.low_stock_enabled && data.low_stock_items_count > 0) {
    alerts.push({
      id: 'low_stock',
      severity: 'warning',
      message: `${data.low_stock_items_count} artículo${data.low_stock_items_count > 1 ? 's' : ''} con stock bajo mínimo`,
      count: data.low_stock_items_count,
    })
  }

  return alerts
}

// ── Sub-components ─────────────────────────────────────────────────────────

const SEVERITY_STYLES = {
  danger:  'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info:    'border-blue-200 bg-blue-50 text-blue-800',
}

const SEVERITY_ICON_COLOR = {
  danger:  'text-red-500',
  warning: 'text-amber-500',
  info:    'text-blue-500',
}

function AlertRow({ alert }: { alert: ActiveAlert }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-xs ${SEVERITY_STYLES[alert.severity]}`}
    >
      <AlertTriangle
        size={13}
        className={`mt-0.5 shrink-0 ${SEVERITY_ICON_COLOR[alert.severity]}`}
      />
      <span>{alert.message}</span>
    </div>
  )
}

function ConfigForm({
  config,
  onChange,
}: {
  config: AlertConfig
  onChange: (c: AlertConfig) => void
}) {
  return (
    <div className="border-t border-gray-100 bg-gray-50 px-4 py-3 space-y-3">
      <p className="text-xs font-semibold text-gray-600">Configurar umbrales</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="flex items-center justify-between gap-2">
          <span className="text-xs text-gray-600">Presupuestos sin respuesta (días)</span>
          <input
            type="number"
            min={1}
            max={90}
            value={config.pending_budget_days}
            onChange={(e) =>
              onChange({ ...config, pending_budget_days: Math.max(1, Number(e.target.value)) })
            }
            className="w-16 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </label>

        <label className="flex items-center justify-between gap-2">
          <span className="text-xs text-gray-600">Facturas vencidas mín. (días)</span>
          <input
            type="number"
            min={0}
            max={365}
            value={config.overdue_invoice_min_days}
            onChange={(e) =>
              onChange({ ...config, overdue_invoice_min_days: Math.max(0, Number(e.target.value)) })
            }
            className="w-16 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </label>

        <label className="flex items-center justify-between gap-2">
          <span className="text-xs text-gray-600">Alerta obras pendientes de cierre</span>
          <input
            type="checkbox"
            checked={config.pending_closure_enabled}
            onChange={(e) => onChange({ ...config, pending_closure_enabled: e.target.checked })}
            className="accent-blue-500"
          />
        </label>

        <label className="flex items-center justify-between gap-2">
          <span className="text-xs text-gray-600">Alerta stock bajo mínimos</span>
          <input
            type="checkbox"
            checked={config.low_stock_enabled}
            onChange={(e) => onChange({ ...config, low_stock_enabled: e.target.checked })}
            className="accent-blue-500"
          />
        </label>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

interface Props {
  data: DashboardSummary
}

export function CustomAlertsPanel({ data }: Props) {
  const [config, setConfig] = useState<AlertConfig>(loadConfig)
  const [showConfig, setShowConfig] = useState(false)

  useEffect(() => {
    saveConfig(config)
  }, [config])

  const alerts = computeAlerts(data, config)

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {alerts.length > 0 ? (
            <Bell size={14} className="text-amber-500" />
          ) : (
            <BellOff size={14} className="text-gray-300" />
          )}
          <h3 className="text-sm font-semibold text-gray-700">Alertas</h3>
          {alerts.length > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-500 text-white text-xs font-bold">
              {alerts.length}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowConfig((v) => !v)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          <Settings size={13} />
          {showConfig ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      <div className="px-4 py-3 space-y-2">
        {alerts.length === 0 ? (
          <p className="text-xs text-gray-400 py-2 text-center">
            Sin alertas activas — todo en orden
          </p>
        ) : (
          alerts.map((a) => <AlertRow key={a.id} alert={a} />)
        )}
      </div>

      {showConfig && <ConfigForm config={config} onChange={setConfig} />}
    </div>
  )
}
