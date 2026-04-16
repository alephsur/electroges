import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Layers, BarChart2, Download, Send, X, GitBranch, CheckCircle, ArrowLeft, Trash2 } from 'lucide-react'
import type { Budget } from '../types'
import { useBudgetStore } from '../store/budget-store'
import {
  useAcceptBudget,
  useCreateNewVersion,
  useDeleteBudget,
  useRejectBudget,
  useSendBudget,
  useWorkOrderPreview,
} from '../hooks/use-budgets'
import { useGeneratePdf } from '../hooks/use-budget-pdf'
import { BudgetStatusBadge } from './BudgetStatusBadge'
import { BudgetMarginIndicator } from './BudgetMarginIndicator'
import { BudgetLineEditor } from './BudgetLineEditor'
import { BudgetTotalsPanel } from './BudgetTotalsPanel'
import { BudgetVersionHistory } from './BudgetVersionHistory'
import { WorkOrderPreviewModal } from './WorkOrderPreviewModal'

interface BudgetDetailProps {
  budget: Budget
}

export function BudgetDetail({ budget }: BudgetDetailProps) {
  const { activeTab, setActiveTab } = useBudgetStore()
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const navigate = useNavigate()

  const sendBudget = useSendBudget()
  const rejectBudget = useRejectBudget()
  const newVersion = useCreateNewVersion()
  const acceptBudget = useAcceptBudget()
  const deleteBudget = useDeleteBudget()
  const generatePdf = useGeneratePdf(budget.id)

  const { data: preview, isLoading: previewLoading } = useWorkOrderPreview(
    showPreviewModal ? budget.id : null,
  )

  const isDraft = budget.status === 'draft'
  const isSent = budget.effective_status === 'sent'
  const isAccepted = budget.status === 'accepted'
  const isRejected = budget.status === 'rejected'
  const isExpired = budget.effective_status === 'expired'
  const canDelete = isDraft || isRejected

  const handleDelete = () => {
    deleteBudget.mutate(budget.id, {
      onSuccess: () => {
        setShowDeleteConfirm(false)
        navigate('/presupuestos')
      },
    })
  }

  const TABS = [
    { id: 'lineas' as const, label: `Líneas (${budget.lines_count})`, icon: <FileText size={13} /> },
    { id: 'totales' as const, label: 'Totales', icon: <BarChart2 size={13} /> },
    { id: 'versiones' as const, label: 'Versiones', icon: <Layers size={13} /> },
  ]

  const handleGeneratePdf = async () => {
    const blobUrl = await generatePdf.mutateAsync()
    window.open(blobUrl, '_blank')
  }

  const handleConfirmAccept = () => {
    acceptBudget.mutate(budget.id, {
      onSuccess: (data) => {
        setShowPreviewModal(false)
        if (data?.work_order_id) {
          navigate(`/obras/${data.work_order_id}`)
        }
      },
    })
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Mobile back button */}
      <button
        onClick={() => navigate('/presupuestos')}
        className="flex items-center gap-1.5 px-4 pt-3 pb-1 text-sm text-gray-500 hover:text-gray-700 lg:hidden"
      >
        <ArrowLeft size={14} />
        Presupuestos
      </button>

      {/* Header */}
      <div className="shrink-0 border-b border-gray-100 p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-gray-900">{budget.budget_number}</span>
              {budget.version > 1 && (
                <span className="text-xs text-gray-400">v{budget.version}</span>
              )}
              <BudgetStatusBadge status={budget.effective_status} />
              <BudgetMarginIndicator
                marginPct={budget.gross_margin_pct}
                marginStatus={budget.margin_status}
              />
            </div>
            <div className="mt-1 text-sm font-semibold text-gray-700">
              {budget.customer_name}
            </div>
            <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500">
              <span>Emitido: {new Date(budget.issue_date).toLocaleDateString('es-ES')}</span>
              <span
                className={
                  isExpired ? 'text-amber-600 font-medium' : ''
                }
              >
                Válido hasta: {new Date(budget.valid_until).toLocaleDateString('es-ES')}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-gray-900">
              {budget.total.toLocaleString('es-ES', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              €
            </div>
            <div className="text-xs text-gray-400">{budget.lines_count} líneas</div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {isDraft && (
            <>
              <button
                onClick={() => sendBudget.mutate(budget.id)}
                disabled={sendBudget.isPending || budget.lines_count === 0}
                className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <Send size={13} />
                Enviar al cliente
              </button>
              <button
                onClick={handleGeneratePdf}
                disabled={generatePdf.isPending}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Download size={13} />
                {generatePdf.isPending ? 'Generando...' : 'Generar PDF'}
              </button>
            </>
          )}
          {isSent && (
            <>
              <button
                onClick={() => setShowPreviewModal(true)}
                className="flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
              >
                <CheckCircle size={13} />
                Aceptar
              </button>
              <button
                onClick={() => rejectBudget.mutate({ id: budget.id })}
                disabled={rejectBudget.isPending}
                className="flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <X size={13} />
                Rechazar
              </button>
              <button
                onClick={() => newVersion.mutate(budget.id)}
                disabled={newVersion.isPending}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <GitBranch size={13} />
                Nueva versión
              </button>
              <button
                onClick={handleGeneratePdf}
                disabled={generatePdf.isPending}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Download size={13} />
                PDF
              </button>
            </>
          )}
          {(isRejected || isExpired) && (
            <>
              <button
                onClick={() => newVersion.mutate(budget.id)}
                disabled={newVersion.isPending}
                className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <GitBranch size={13} />
                Nueva versión
              </button>
              <button
                onClick={handleGeneratePdf}
                disabled={generatePdf.isPending}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Download size={13} />
                PDF
              </button>
            </>
          )}
          {isAccepted && (
            <>
              <button
                disabled
                className="flex items-center gap-1.5 cursor-not-allowed rounded-md bg-gray-100 px-3 py-1.5 text-xs text-gray-400"
              >
                Ver obra (próximamente)
              </button>
              <button
                onClick={handleGeneratePdf}
                disabled={generatePdf.isPending}
                className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Download size={13} />
                PDF
              </button>
            </>
          )}
          {canDelete && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 ml-auto"
            >
              <Trash2 size={13} />
              Eliminar
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="shrink-0 border-b border-gray-100 px-4">
        <div className="-mb-px flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'lineas' && (
          <BudgetLineEditor
            budgetId={budget.id}
            lines={budget.lines}
            readOnly={!isDraft}
          />
        )}
        {activeTab === 'totales' && <BudgetTotalsPanel budget={budget} />}
        {activeTab === 'versiones' && (
          <BudgetVersionHistory budgetId={budget.id} />
        )}
      </div>

      {/* WorkOrder preview modal */}
      {showPreviewModal && preview && (
        <WorkOrderPreviewModal
          preview={preview}
          isConfirming={acceptBudget.isPending}
          onConfirm={handleConfirmAccept}
          onClose={() => setShowPreviewModal(false)}
        />
      )}
      {showPreviewModal && previewLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="rounded-xl bg-white px-8 py-6 text-sm text-gray-600">
            Cargando vista previa...
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white shadow-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                <Trash2 size={18} className="text-red-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Eliminar presupuesto</h3>
                <p className="text-xs text-gray-500">{budget.budget_number}</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              Esta acción es permanente y no se puede deshacer. ¿Confirmas que quieres eliminar este presupuesto?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteBudget.isPending}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteBudget.isPending}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteBudget.isPending ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
