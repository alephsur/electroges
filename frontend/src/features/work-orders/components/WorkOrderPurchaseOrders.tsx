import { useState } from 'react'
import { CheckCircle, ChevronDown, ChevronRight, Link, Mail, MessageCircle, Package, Plus, Unlink } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { useReceivePurchaseOrderFromWorkOrder, useUnlinkPurchaseOrder } from '../hooks/use-work-order-purchase-orders'
import { NewPurchaseOrderModal } from './NewPurchaseOrderModal'
import { LinkExistingPOModal } from './LinkExistingPOModal'
import type { LinkedPurchaseOrder, WorkOrder } from '../types'

function fmt(n: number | string) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtQty(n: number | string) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
}

const PO_STATUS: Record<string, { label: string; className: string }> = {
  pending:   { label: 'Pendiente',  className: 'bg-amber-100 text-amber-700' },
  received:  { label: 'Recibido',   className: 'bg-green-100 text-green-700' },
  cancelled: { label: 'Cancelado',  className: 'bg-gray-100 text-gray-500' },
}

// ── WhatsApp / Email helpers ──────────────────────────────────────────────────

function buildPOMessage(po: LinkedPurchaseOrder, workOrderNumber?: string): string {
  const header = workOrderNumber
    ? `Pedido ${po.order_number} (Obra ${workOrderNumber})`
    : `Pedido ${po.order_number}`

  const lines = po.lines.map((l) => {
    const name = l.inventory_item_name ?? l.description ?? '—'
    return `• ${name}: ${fmtQty(l.quantity)} ud × ${fmt(l.unit_cost)} € = ${fmt(l.subtotal)} €`
  })

  return [
    header,
    `Fecha: ${po.order_date}`,
    po.expected_date ? `Entrega prevista: ${po.expected_date}` : '',
    '',
    ...lines,
    '',
    `Total: ${fmt(Number(po.total_amount))} €`,
    po.notes ? `\nNotas: ${po.notes}` : '',
  ]
    .filter((l) => l !== undefined)
    .join('\n')
    .trim()
}

function whatsappUrl(phone: string, message: string): string {
  const clean = phone.replace(/[\s\-().+]/g, '')
  const intl = clean.startsWith('0') ? `34${clean.slice(1)}` : clean
  return `https://wa.me/${intl}?text=${encodeURIComponent(message)}`
}

function mailtoUrl(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

// ── PO row with expandable detail ─────────────────────────────────────────────

interface PORowProps {
  link: LinkedPurchaseOrder
  workOrderNumber: string
  onUnlink: () => void
  unlinkPending: boolean
  onReceive: () => void
  receivePending: boolean
}

function PORow({ link, workOrderNumber, onUnlink, unlinkPending, onReceive, receivePending }: PORowProps) {
  const [expanded, setExpanded] = useState(false)
  const cfg = PO_STATUS[link.status] ?? { label: link.status, className: 'bg-gray-100 text-gray-600' }
  const message = buildPOMessage(link, workOrderNumber)

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-3 p-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 text-gray-400 hover:text-gray-600"
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">{link.order_number}</span>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}>
              {cfg.label}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-gray-500">
            {link.supplier_name}
            <span className="mx-1.5 text-gray-300">·</span>
            {fmt(Number(link.total_amount))} €
            <span className="mx-1.5 text-gray-300">·</span>
            {link.order_date}
            {link.expected_date && (
              <span className="ml-1 text-gray-400">(entrega: {link.expected_date})</span>
            )}
          </p>
          {link.notes && <p className="mt-0.5 text-xs text-gray-400">{link.notes}</p>}
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 items-center gap-1">
          {link.status === 'pending' && (
            <button
              onClick={onReceive}
              disabled={receivePending}
              title="Marcar como recibido"
              className="flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1.5 text-xs font-medium text-emerald-600 hover:border-emerald-300 hover:bg-emerald-50 disabled:opacity-50"
            >
              <CheckCircle size={13} />
              Recibir
            </button>
          )}
          {link.supplier_phone && (
            <a
              href={whatsappUrl(link.supplier_phone, message)}
              target="_blank"
              rel="noopener noreferrer"
              title={`WhatsApp a ${link.supplier_name} (${link.supplier_phone})`}
              className="rounded-md border border-gray-200 p-1.5 text-green-500 hover:border-green-300 hover:bg-green-50"
            >
              <MessageCircle size={14} />
            </a>
          )}
          {link.supplier_email && (
            <a
              href={mailtoUrl(
                link.supplier_email,
                `Pedido ${link.order_number}`,
                message,
              )}
              title={`Email a ${link.supplier_email}`}
              className="rounded-md border border-gray-200 p-1.5 text-blue-500 hover:border-blue-300 hover:bg-blue-50"
            >
              <Mail size={14} />
            </a>
          )}
          <button
            onClick={onUnlink}
            disabled={unlinkPending}
            title="Desvincular pedido"
            className="rounded-md border border-gray-200 p-1.5 text-gray-400 hover:border-red-200 hover:text-red-500 disabled:opacity-50"
          >
            <Unlink size={14} />
          </button>
        </div>
      </div>

      {/* Expanded detail: lines table */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3">
          {link.lines.length === 0 ? (
            <p className="text-xs text-gray-400">Sin líneas registradas.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="pb-1.5 text-xs font-medium text-gray-500">Artículo / descripción</th>
                  <th className="pb-1.5 text-right text-xs font-medium text-gray-500">Cantidad</th>
                  <th className="pb-1.5 text-right text-xs font-medium text-gray-500">€/ud</th>
                  <th className="pb-1.5 text-right text-xs font-medium text-gray-500">Subtotal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {link.lines.map((line, i) => (
                  <tr key={i}>
                    <td className="py-1.5 pr-3 text-gray-800">
                      {line.inventory_item_name ?? line.description ?? '—'}
                    </td>
                    <td className="py-1.5 pr-3 text-right text-gray-600">
                      {fmtQty(line.quantity)}
                    </td>
                    <td className="py-1.5 pr-3 text-right text-gray-600">
                      {fmt(line.unit_cost)} €
                    </td>
                    <td className="py-1.5 text-right font-medium text-gray-900">
                      {fmt(line.subtotal)} €
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-gray-200">
                  <td colSpan={3} className="pt-2 text-right text-xs font-semibold text-gray-500">
                    Total
                  </td>
                  <td className="pt-2 text-right text-sm font-bold text-gray-900">
                    {fmt(Number(link.total_amount))} €
                  </td>
                </tr>
              </tfoot>
            </table>
          )}

          {/* Contact info reminder */}
          {(link.supplier_email || link.supplier_phone) && (
            <div className="mt-3 flex flex-wrap gap-3 border-t border-gray-50 pt-3">
              {link.supplier_phone && (
                <span className="text-xs text-gray-400">
                  Tel: {link.supplier_phone}
                </span>
              )}
              {link.supplier_email && (
                <span className="text-xs text-gray-400">
                  Email: {link.supplier_email}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface WorkOrderPurchaseOrdersProps {
  workOrder: WorkOrder
}

export function WorkOrderPurchaseOrders({ workOrder }: WorkOrderPurchaseOrdersProps) {
  const [showNewModal, setShowNewModal] = useState(false)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const unlink = useUnlinkPurchaseOrder()
  const receive = useReceivePurchaseOrderFromWorkOrder()

  const links = workOrder.purchase_order_links ?? []

  const handleUnlink = async (purchaseOrderId: string, orderNumber: string) => {
    if (!confirm(`¿Desvincular el pedido ${orderNumber} de esta obra?`)) return
    try {
      await unlink.mutateAsync({ workOrderId: workOrder.id, purchaseOrderId })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const handleReceive = async (purchaseOrderId: string, orderNumber: string) => {
    if (!confirm(`¿Marcar el pedido ${orderNumber} como recibido? Los materiales del pedido se añadirán a las tareas de esta obra.`)) return
    try {
      await receive.mutateAsync({ workOrderId: workOrder.id, purchaseOrderId })
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  return (
    <div className="space-y-3">
      {/* Summary */}
      {links.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-1">
          <div className="rounded-lg bg-gray-50 px-4 py-3">
            <p className="text-xs text-gray-500">Pedidos</p>
            <p className="text-lg font-semibold text-gray-900">{links.length}</p>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3">
            <p className="text-xs text-gray-500">Pendientes</p>
            <p className="text-lg font-semibold text-amber-600">
              {links.filter((l) => l.status === 'pending').length}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 px-4 py-3">
            <p className="text-xs text-gray-500">Importe total</p>
            <p className="text-lg font-semibold text-gray-900">
              {fmt(links.reduce((acc, l) => acc + Number(l.total_amount), 0))} €
            </p>
          </div>
        </div>
      )}

      {/* PO list */}
      {links.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Package size={32} className="mb-2 text-gray-200" />
          <p className="text-sm text-gray-400">No hay pedidos vinculados a esta obra.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {links.map((link) => (
            <PORow
              key={link.id}
              link={link}
              workOrderNumber={workOrder.work_order_number}
              onUnlink={() => handleUnlink(link.purchase_order_id, link.order_number)}
              unlinkPending={unlink.isPending}
              onReceive={() => handleReceive(link.purchase_order_id, link.order_number)}
              receivePending={receive.isPending}
            />
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowNewModal(true)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600"
        >
          <Plus size={14} />
          Nuevo pedido
        </button>
        <button
          onClick={() => setShowLinkModal(true)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Link size={14} />
          Vincular existente
        </button>
      </div>

      {showNewModal && (
        <NewPurchaseOrderModal
          workOrderId={workOrder.id}
          onClose={() => setShowNewModal(false)}
        />
      )}

      {showLinkModal && (
        <LinkExistingPOModal
          workOrderId={workOrder.id}
          alreadyLinkedIds={links.map((l) => l.purchase_order_id)}
          onClose={() => setShowLinkModal(false)}
        />
      )}
    </div>
  )
}
