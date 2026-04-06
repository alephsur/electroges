import { useState } from 'react'
import { Routes, Route, useMatch, useParams, useNavigate } from 'react-router-dom'
import { Search, Plus, FileText, ArrowLeft } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { useInvoices } from '../hooks/use-invoices'
import { useInvoiceStore } from '../store/invoice-store'
import { InvoiceList } from './InvoiceList'
import { InvoiceDetail } from './InvoiceDetail'
import { InvoiceFromWorkOrderForm } from './InvoiceFromWorkOrderForm'

type NewInvoiceMode = null | 'from-work-order'

const STATUS_OPTIONS = [
  { value: '', label: 'Todos los estados' },
  { value: 'draft', label: 'Borrador' },
  { value: 'sent', label: 'Enviada' },
  { value: 'overdue', label: 'Vencida' },
  { value: 'partially_paid', label: 'Cobro parcial' },
  { value: 'paid', label: 'Cobrada' },
  { value: 'cancelled', label: 'Anulada' },
]

function InvoiceDetailRoute() {
  const { invoiceId } = useParams<{ invoiceId: string }>()
  if (!invoiceId) return null
  return <InvoiceDetail invoiceId={invoiceId} />
}

export function InvoicingPage() {
  const [newInvoiceMode, setNewInvoiceMode] = useState<NewInvoiceMode>(null)
  const navigate = useNavigate()
  const {
    searchQuery,
    statusFilter,
    overdueOnly,
    setSearchQuery,
    setStatusFilter,
    setOverdueOnly,
  } = useInvoiceStore()

  const debouncedQuery = useDebounce(searchQuery, 300)

  const isEffectiveOverdue = statusFilter === 'overdue'
  const apiStatus =
    statusFilter && !['overdue', 'partially_paid'].includes(statusFilter)
      ? statusFilter
      : undefined

  const { data, isLoading } = useInvoices({
    q: debouncedQuery || undefined,
    status: apiStatus,
    overdue_only: overdueOnly || isEffectiveOverdue || undefined,
    limit: 100,
  })

  const invoices = data?.items ?? []
  const filteredInvoices =
    statusFilter === 'partially_paid'
      ? invoices.filter((inv) => inv.effective_status === 'partially_paid')
      : invoices

  const detailMatch = useMatch('/facturacion/:invoiceId')
  const isDetailSelected = !!detailMatch
  const isRightPanelActive = isDetailSelected || newInvoiceMode !== null

  return (
    <div className="flex h-full gap-0">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex shrink-0 flex-col border-r border-gray-100 bg-white',
          isRightPanelActive
            ? 'hidden lg:flex lg:w-80'
            : 'flex w-full lg:w-80',
        )}
      >
        {/* Search + filters */}
        <div className="border-b border-gray-100 p-3 space-y-2">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Buscar facturas…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-8 pr-3 text-sm outline-none focus:border-blue-400 focus:bg-white"
            />
          </div>
          <select
            value={statusFilter ?? ''}
            onChange={(e) => setStatusFilter((e.target.value as any) || null)}
            className="w-full rounded border border-gray-200 bg-gray-50 px-2 py-1.5 text-xs outline-none focus:border-blue-400"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded"
            />
            Solo vencidas
          </label>
        </div>

        {/* New invoice button */}
        <div className="border-b border-gray-100 p-3">
          <button
            onClick={() => setNewInvoiceMode('from-work-order')}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus size={14} /> Nueva factura
          </button>
        </div>

        {/* Invoice list */}
        <div className="flex-1 overflow-y-auto">
          {data && (
            <div className="border-b border-gray-100 px-3 py-1.5 text-xs text-gray-400">
              {data.total} factura{data.total !== 1 ? 's' : ''}
            </div>
          )}
          <InvoiceList invoices={filteredInvoices} isLoading={isLoading} />
        </div>
      </div>

      {/* Right panel */}
      <div
        className={cn(
          'flex-1 overflow-hidden bg-white',
          !isRightPanelActive && 'hidden lg:block',
        )}
      >
        {newInvoiceMode === 'from-work-order' ? (
          <div className="h-full overflow-y-auto p-4 lg:p-6">
            {/* Mobile back button */}
            <button
              onClick={() => setNewInvoiceMode(null)}
              className="flex items-center gap-1.5 mb-4 text-sm text-gray-500 hover:text-gray-700 lg:hidden"
            >
              <ArrowLeft size={14} />
              Facturas
            </button>
            <div className="mx-auto max-w-xl">
              <h2 className="mb-4 text-lg font-semibold text-gray-800">
                Nueva factura desde obra
              </h2>
              <InvoiceFromWorkOrderForm
                onSuccess={(id) => {
                  setNewInvoiceMode(null)
                  navigate(`/facturacion/${id}`)
                }}
                onCancel={() => setNewInvoiceMode(null)}
              />
            </div>
          </div>
        ) : (
          <Routes>
            <Route
              index
              element={
                <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
                  <FileText size={48} strokeWidth={1} />
                  <p className="text-sm">Selecciona una factura para ver el detalle</p>
                  <button
                    onClick={() => setNewInvoiceMode('from-work-order')}
                    className="flex items-center gap-1.5 rounded-lg border border-blue-200 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50"
                  >
                    <Plus size={14} /> Nueva factura desde obra
                  </button>
                </div>
              }
            />
            <Route path=":invoiceId" element={<InvoiceDetailRoute />} />
          </Routes>
        )}
      </div>
    </div>
  )
}
