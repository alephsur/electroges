import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Send,
  FileText,
  Download,
  XCircle,
  RefreshCw,
  Bell,
  Plus,
  ArrowLeft,
} from 'lucide-react'
import { useInvoice, useSendInvoice, useCancelInvoice } from '../hooks/use-invoices'
import { useGenerateInvoicePdf, useDownloadInvoicePdf } from '../hooks/use-invoice-pdf'
import { InvoiceStatusBadge } from './InvoiceStatusBadge'
import { PaymentProgressBar } from './PaymentProgressBar'
import { InvoiceLineEditor } from './InvoiceLineEditor'
import { InvoiceTotalsPanel } from './InvoiceTotalsPanel'
import { PaymentList } from './PaymentList'
import { PaymentForm } from './PaymentForm'
import { RectificationModal } from './RectificationModal'
import { ReminderModal } from './ReminderModal'
import { apiClient } from '@/lib/api-client'
import type { PaymentReminderResponse } from '../types'

type ActiveTab = 'lines' | 'payments' | 'notes'

interface Props {
  invoiceId: string
}

export function InvoiceDetail({ invoiceId }: Props) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('lines')
  const [showPaymentForm, setShowPaymentForm] = useState(false)
  const [showRectModal, setShowRectModal] = useState(false)
  const [showReminderModal, setShowReminderModal] = useState(false)
  const [reminder, setReminder] = useState<PaymentReminderResponse | null>(null)

  const { data: invoice, isLoading } = useInvoice(invoiceId)
  const { mutate: sendInvoice, isPending: isSending } = useSendInvoice()
  const { mutate: cancelInvoice, isPending: isCancelling } = useCancelInvoice()
  const { mutate: generatePdf, isPending: isGenerating } =
    useGenerateInvoicePdf(invoiceId)
  const { mutate: downloadPdf, isPending: isDownloading } =
    useDownloadInvoicePdf(
      invoiceId,
      invoice?.invoice_number ?? '',
    )

  async function handleLoadReminder() {
    const { data } = await apiClient.get<PaymentReminderResponse>(
      `/api/v1/invoices/${invoiceId}/reminder`,
    )
    setReminder(data)
    setShowReminderModal(true)
  }

  if (isLoading || !invoice) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const isDraft = invoice.status === 'draft'
  const isSent = invoice.status === 'sent'
  const isPaid = invoice.status === 'paid'
  const isCancelled = invoice.status === 'cancelled'
  const isOverdue = invoice.effective_status === 'overdue'
  const isPartiallyPaid = invoice.effective_status === 'partially_paid'

  const tabs: { key: ActiveTab; label: string }[] = [
    { key: 'lines', label: 'Líneas y totales' },
    { key: 'payments', label: `Cobros (${invoice.payments.length})` },
    { key: 'notes', label: 'Notas' },
  ]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Mobile back button */}
      <button
        onClick={() => navigate('/facturacion')}
        className="flex items-center gap-1.5 px-4 pt-3 pb-1 text-sm text-gray-500 hover:text-gray-700 lg:hidden"
      >
        <ArrowLeft size={14} />
        Facturas
      </button>

      {/* Header */}
      <div className="border-b border-gray-100 bg-white p-4">
        {/* Top row */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {invoice.is_rectification && (
                <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
                  RECTIFICATIVA
                </span>
              )}
              <h2 className="text-lg font-bold text-gray-800">
                {invoice.invoice_number}
              </h2>
              <InvoiceStatusBadge status={invoice.effective_status} />
              {isOverdue && (
                <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">
                  Vencida hace {invoice.days_overdue} días
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm text-gray-600">
              {invoice.customer_name}
              {invoice.work_order_number && (
                <span className="ml-2 text-gray-400">
                  · Obra {invoice.work_order_number}
                </span>
              )}
            </p>
            {invoice.is_rectification && invoice.rectifies_invoice_id && (
              <p className="mt-1 text-xs text-blue-600">
                Rectifica la factura anterior
              </p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-1.5 shrink-0">
            {isDraft && (
              <>
                <button
                  onClick={() => sendInvoice(invoiceId)}
                  disabled={isSending || invoice.lines.length === 0}
                  className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <Send size={12} /> Enviar
                </button>
                <button
                  onClick={() => generatePdf()}
                  disabled={isGenerating}
                  className="flex items-center gap-1 rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  <FileText size={12} />{' '}
                  {isGenerating ? 'Generando…' : 'Generar PDF'}
                </button>
                <button
                  onClick={() => {
                    const reason = window.prompt('Motivo de cancelación:')
                    if (reason)
                      cancelInvoice({ id: invoiceId, reason })
                  }}
                  disabled={isCancelling}
                  className="flex items-center gap-1 rounded border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircle size={12} /> Cancelar
                </button>
              </>
            )}
            {(isSent || isOverdue || isPartiallyPaid) && (
              <>
                <button
                  onClick={() => {
                    setShowPaymentForm(true)
                    setActiveTab('payments')
                  }}
                  className="flex items-center gap-1 rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                >
                  <Plus size={12} /> Registrar cobro
                </button>
                {invoice.has_pdf ? (
                  <button
                    onClick={() => downloadPdf()}
                    disabled={isDownloading}
                    className="flex items-center gap-1 rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <Download size={12} /> Descargar PDF
                  </button>
                ) : (
                  <button
                    onClick={() => generatePdf()}
                    disabled={isGenerating}
                    className="flex items-center gap-1 rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <FileText size={12} />{' '}
                    {isGenerating ? 'Generando…' : 'Generar PDF'}
                  </button>
                )}
                <button
                  onClick={() => setShowRectModal(true)}
                  className="flex items-center gap-1 rounded border border-orange-200 px-3 py-1.5 text-xs text-orange-600 hover:bg-orange-50"
                >
                  <RefreshCw size={12} /> Rectificar
                </button>
                <button
                  onClick={handleLoadReminder}
                  className="flex items-center gap-1 rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
                >
                  <Bell size={12} /> Recordatorio
                </button>
              </>
            )}
            {isPaid && invoice.has_pdf && (
              <button
                onClick={() => downloadPdf()}
                disabled={isDownloading}
                className="flex items-center gap-1 rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Download size={12} /> Descargar PDF
              </button>
            )}
          </div>
        </div>

        {/* Payment progress */}
        <div className="mt-3">
          <PaymentProgressBar
            total={invoice.totals.total}
            total_paid={invoice.totals.total_paid}
            pending_amount={invoice.totals.pending_amount}
            effective_status={invoice.effective_status}
          />
        </div>

        {/* Dates */}
        <div className="mt-2 flex gap-4 text-xs text-gray-500">
          <span>
            Emitida:{' '}
            <strong>
              {new Date(invoice.issue_date).toLocaleDateString('es-ES')}
            </strong>
          </span>
          <span
            className={
              isOverdue ? 'font-medium text-red-600' : ''
            }
          >
            Vence:{' '}
            <strong>
              {new Date(invoice.due_date).toLocaleDateString('es-ES')}
            </strong>
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100 bg-white px-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`mr-4 py-2 text-sm transition-colors ${
              activeTab === t.key
                ? 'border-b-2 border-blue-600 font-medium text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'lines' && (
          <div>
            <InvoiceLineEditor
              invoiceId={invoiceId}
              lines={invoice.lines}
              isEditable={isDraft}
            />
            <div className="mt-4 flex justify-end">
              <InvoiceTotalsPanel
                totals={invoice.totals}
                tax_rate={invoice.tax_rate}
                discount_pct={invoice.discount_pct}
              />
            </div>
          </div>
        )}

        {activeTab === 'payments' && (
          <div className="space-y-4">
            {showPaymentForm && isSent && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                <h3 className="mb-3 text-sm font-medium text-gray-700">
                  Registrar cobro
                </h3>
                <PaymentForm
                  invoiceId={invoiceId}
                  pendingAmount={invoice.totals.pending_amount}
                  onSuccess={() => setShowPaymentForm(false)}
                  onCancel={() => setShowPaymentForm(false)}
                />
              </div>
            )}
            <PaymentList
              invoiceId={invoiceId}
              payments={invoice.payments}
              canDelete={!isCancelled}
            />
            <div className="mt-4">
              <PaymentProgressBar
                total={invoice.totals.total}
                total_paid={invoice.totals.total_paid}
                pending_amount={invoice.totals.pending_amount}
                effective_status={invoice.effective_status}
              />
            </div>
          </div>
        )}

        {activeTab === 'notes' && (
          <div className="space-y-4">
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500">
                Notas internas{' '}
                <span className="text-gray-400">(no aparecen en el PDF)</span>
              </p>
              <div className="rounded border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700 whitespace-pre-wrap">
                {invoice.notes || (
                  <span className="text-gray-400">Sin notas internas</span>
                )}
              </div>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500">
                Notas para el cliente{' '}
                <span className="text-gray-400">(aparecen en el PDF)</span>
              </p>
              <div className="rounded border border-gray-200 bg-amber-50 p-3 text-sm text-gray-700 whitespace-pre-wrap">
                {invoice.client_notes || (
                  <span className="text-gray-400">Sin notas para el cliente</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showRectModal && (
        <RectificationModal
          invoiceId={invoiceId}
          invoiceNumber={invoice.invoice_number}
          onSuccess={(newId) => {
            setShowRectModal(false)
            navigate(`/facturacion/${newId}`)
          }}
          onClose={() => setShowRectModal(false)}
        />
      )}
      {showReminderModal && reminder && (
        <ReminderModal
          reminder={reminder}
          onClose={() => setShowReminderModal(false)}
        />
      )}
    </div>
  )
}
