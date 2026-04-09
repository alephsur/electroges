import { useState } from 'react'
import { Routes, Route, useMatch, useParams, useNavigate } from 'react-router-dom'
import { Search, Plus, FileText, ArrowLeft, Receipt } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { useInvoices } from '../hooks/use-invoices'
import { useInvoiceStore, PAGE_SIZE_OPTIONS } from '../store/invoice-store'
import type { PageSize } from '../store/invoice-store'
import { InvoiceList } from './InvoiceList'
import { InvoiceDetail } from './InvoiceDetail'
import { InvoiceFromWorkOrderForm } from './InvoiceFromWorkOrderForm'

type NewInvoiceMode = null | 'from-work-order'

const STATUS_OPTIONS = [
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
    page,
    pageSize,
    setSearchQuery,
    setStatusFilter,
    setOverdueOnly,
    setPage,
    setPageSize,
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
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  const invoices = data?.items ?? []
  const filteredInvoices =
    statusFilter === 'partially_paid'
      ? invoices.filter((inv) => inv.effective_status === 'partially_paid')
      : invoices
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  const detailMatch = useMatch('/facturacion/:invoiceId')
  const isDetailSelected = !!detailMatch
  const isRightPanelActive = isDetailSelected || newInvoiceMode !== null

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex flex-col border-r border-gray-100 min-w-0',
          isRightPanelActive
            ? 'hidden lg:flex lg:w-[42%] lg:shrink-0'
            : 'flex flex-1',
        )}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Receipt size={18} className="text-gray-600" />
              <h1 className="text-lg font-semibold text-gray-900">Facturación</h1>
              {data && (
                <span className="text-sm text-gray-400">({data.total})</span>
              )}
            </div>
            <button
              onClick={() => setNewInvoiceMode('from-work-order')}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus size={15} />
              <span className="hidden sm:inline">Nueva factura</span>
              <span className="sm:hidden">Nueva</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Buscar facturas…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status filter pills */}
          <div className="flex flex-wrap gap-1.5 mb-2">
            <button
              onClick={() => setStatusFilter(null)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                statusFilter === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Todas
            </button>
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() =>
                  setStatusFilter((opt.value === statusFilter ? null : opt.value) as any)
                }
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                  statusFilter === opt.value
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Solo vencidas toggle */}
          <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded"
            />
            Solo vencidas
          </label>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          <InvoiceList invoices={filteredInvoices} isLoading={isLoading} />
        </div>

        {/* Pagination */}
        {!isLoading && data && data.total > 0 && (
          <div className="shrink-0 border-t border-gray-100 px-4 py-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span>Por página:</span>
              {PAGE_SIZE_OPTIONS.map((size) => (
                <button
                  key={size}
                  onClick={() => setPageSize(size as PageSize)}
                  className={`rounded px-2 py-0.5 font-medium transition-colors ${
                    pageSize === size
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, data.total)} de {data.total}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ›
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right panel */}
      <div
        className={cn(
          'flex-1 overflow-hidden bg-white',
          !isRightPanelActive && 'hidden lg:flex',
        )}
      >
        {newInvoiceMode === 'from-work-order' ? (
          <div className="h-full overflow-y-auto p-4 lg:p-6">
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
