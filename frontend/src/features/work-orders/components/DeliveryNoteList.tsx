import { useState } from 'react'
import { Plus, Send, Trash2, X, ChevronDown, ChevronUp, Download, Mail, MessageCircle } from 'lucide-react'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import {
  useCreateDeliveryNote,
  useDeleteDeliveryNote,
  useIssueDeliveryNote,
  useUpdateDeliveryNote,
} from '../hooks/use-delivery-notes'
import {
  useDownloadPdf,
  useOpenWhatsApp,
} from '../hooks/use-document-actions'
import { SendEmailModal } from './SendEmailModal'
import type {
  DeliveryNote,
  DeliveryNoteItemCreate,
  DeliveryNoteLineType,
  WorkOrder,
} from '../types'

function fmt(n: number) {
  return Number(n).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  draft: { label: 'Borrador', className: 'bg-gray-100 text-gray-700' },
  issued: { label: 'Emitido', className: 'bg-blue-100 text-blue-700' },
}

const LINE_TYPE_LABELS: Record<DeliveryNoteLineType, string> = {
  material: 'Material',
  labor: 'Mano de obra',
  other: 'Otro',
}

// ── Empty line template ────────────────────────────────────────────────────────

function emptyLine(): DeliveryNoteItemCreate {
  return {
    line_type: 'material',
    description: '',
    quantity: 1,
    unit: 'ud',
    unit_price: 0,
  }
}

// ── Delivery note form (create / edit) ────────────────────────────────────────

interface DeliveryNoteFormProps {
  workOrderId: string
  initial?: DeliveryNote
  onClose: () => void
}

function DeliveryNoteForm({ workOrderId, initial, onClose }: DeliveryNoteFormProps) {
  const createNote = useCreateDeliveryNote()
  const updateNote = useUpdateDeliveryNote()

  const today = new Date().toISOString().split('T')[0]

  const [deliveryDate, setDeliveryDate] = useState(initial?.delivery_date ?? today)
  const [requestedBy, setRequestedBy] = useState(initial?.requested_by ?? '')
  const [notes, setNotes] = useState(initial?.notes ?? '')
  const [items, setItems] = useState<DeliveryNoteItemCreate[]>(
    initial?.items.map((i) => ({
      line_type: i.line_type,
      description: i.description,
      inventory_item_id: i.inventory_item_id ?? undefined,
      quantity: Number(i.quantity),
      unit: i.unit,
      unit_price: Number(i.unit_price),
      sort_order: i.sort_order,
    })) ?? [emptyLine()],
  )

  const setItem = (idx: number, patch: Partial<DeliveryNoteItemCreate>) =>
    setItems((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)))

  const addLine = () => setItems((prev) => [...prev, emptyLine()])

  const removeLine = (idx: number) =>
    setItems((prev) => prev.filter((_, i) => i !== idx))

  const total = items.reduce((acc, i) => acc + Number(i.quantity) * Number(i.unit_price), 0)

  const handleSubmit = async () => {
    if (!deliveryDate) return
    const payload = {
      delivery_date: deliveryDate,
      requested_by: requestedBy || null,
      notes: notes || null,
      items: items.map((item, idx) => ({ ...item, sort_order: idx })),
    }
    try {
      if (initial) {
        await updateNote.mutateAsync({
          workOrderId,
          deliveryNoteId: initial.id,
          data: payload,
        })
      } else {
        await createNote.mutateAsync({ workOrderId, data: payload })
      }
      onClose()
    } catch (e) {
      alert(getApiErrorMessage(e))
    }
  }

  const isPending = createNote.isPending || updateNote.isPending

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-4">
      <p className="text-sm font-semibold text-gray-800">
        {initial ? 'Editar albarán' : 'Nuevo albarán'}
      </p>

      {/* Header fields */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Fecha de entrega *
          </label>
          <input
            type="date"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Solicitado por
          </label>
          <input
            type="text"
            placeholder="Cliente, jefe de obra…"
            value={requestedBy}
            onChange={(e) => setRequestedBy(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Notas</label>
          <input
            type="text"
            placeholder="Observaciones…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Line items */}
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Líneas
        </p>

        {/* Header row */}
        <div className="hidden grid-cols-[120px_1fr_70px_60px_90px_32px] gap-2 px-1 text-xs font-medium text-gray-500 sm:grid">
          <span>Tipo</span>
          <span>Descripción</span>
          <span className="text-right">Cant.</span>
          <span>Unid.</span>
          <span className="text-right">P. unit.</span>
          <span />
        </div>

        {items.map((item, idx) => (
          <div
            key={idx}
            className="grid grid-cols-1 gap-2 rounded-lg border border-white bg-white p-2 sm:grid-cols-[120px_1fr_70px_60px_90px_32px] sm:items-center"
          >
            <select
              value={item.line_type}
              onChange={(e) =>
                setItem(idx, { line_type: e.target.value as DeliveryNoteLineType })
              }
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            >
              <option value="material">Material</option>
              <option value="labor">Mano de obra</option>
              <option value="other">Otro</option>
            </select>

            <input
              type="text"
              placeholder="Descripción *"
              value={item.description}
              onChange={(e) => setItem(idx, { description: e.target.value })}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />

            <input
              type="number"
              min="0"
              step="0.001"
              placeholder="Cant."
              value={item.quantity}
              onChange={(e) =>
                setItem(idx, { quantity: parseFloat(e.target.value) || 0 })
              }
              className="rounded border border-gray-300 px-2 py-1 text-right text-sm"
            />

            <input
              type="text"
              placeholder="ud"
              value={item.unit}
              onChange={(e) => setItem(idx, { unit: e.target.value })}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />

            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00 €"
              value={item.unit_price}
              onChange={(e) =>
                setItem(idx, { unit_price: parseFloat(e.target.value) || 0 })
              }
              className="rounded border border-gray-300 px-2 py-1 text-right text-sm"
            />

            <button
              onClick={() => removeLine(idx)}
              disabled={items.length === 1}
              className="flex items-center justify-center rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-30"
            >
              <X size={14} />
            </button>
          </div>
        ))}

        <button
          onClick={addLine}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-gray-300 py-2 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={13} />
          Añadir línea
        </button>
      </div>

      {/* Total */}
      <div className="flex justify-end">
        <p className="text-sm font-medium text-gray-700">
          Total: <strong>{fmt(total)} €</strong>
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={isPending || !deliveryDate}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {initial ? 'Guardar cambios' : 'Crear albarán'}
        </button>
        <button
          onClick={onClose}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// ── Delivery note card ─────────────────────────────────────────────────────────

interface DeliveryNoteCardProps {
  note: DeliveryNote
  workOrderId: string
  customerEmail?: string | null
  customerPhone?: string | null
}

function DeliveryNoteCard({
  note,
  workOrderId,
  customerEmail,
  customerPhone,
}: DeliveryNoteCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [showEmail, setShowEmail] = useState(false)
  const issueNote = useIssueDeliveryNote()
  const deleteNote = useDeleteDeliveryNote()
  const { download, isDownloading } = useDownloadPdf()
  const { open: openWhatsApp, isLoading: isWhatsAppLoading } = useOpenWhatsApp()

  const baseUrl = `/api/v1/work-orders/${workOrderId}/delivery-notes/${note.id}`
  const cfg = STATUS_BADGE[note.status] ?? STATUS_BADGE.draft

  if (editing) {
    return (
      <DeliveryNoteForm
        workOrderId={workOrderId}
        initial={note}
        onClose={() => setEditing(false)}
      />
    )
  }

  return (
    <>
      {showEmail && (
        <SendEmailModal
          apiUrl={`${baseUrl}/send-email`}
          defaultEmail={customerEmail ?? ''}
          documentLabel={`albarán ${note.delivery_note_number}`}
          onClose={() => setShowEmail(false)}
        />
      )}

    <div className="rounded-xl border border-gray-100 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-900">
              {note.delivery_note_number}
            </span>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}
            >
              {cfg.label}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
            <span>Fecha: {note.delivery_date}</span>
            {note.requested_by && <span>Solicitado por: {note.requested_by}</span>}
            <span>
              {note.items.length} línea{note.items.length !== 1 ? 's' : ''} ·{' '}
              <strong className="text-gray-700">{fmt(note.total_amount)} €</strong>
            </span>
          </div>
          {note.notes && (
            <p className="mt-1 text-xs text-gray-400">{note.notes}</p>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-1">
          <button
            onClick={() => setExpanded((v) => !v)}
            title={expanded ? 'Ocultar líneas' : 'Ver líneas'}
            className="rounded-md border border-gray-200 p-1.5 text-gray-400 hover:bg-gray-50"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {/* PDF download */}
          <button
            onClick={() =>
              download(`${baseUrl}/pdf`, `${note.delivery_note_number}.pdf`)
            }
            disabled={isDownloading}
            title="Descargar PDF"
            className="rounded-md border border-gray-200 p-1.5 text-gray-500 hover:bg-gray-50 disabled:opacity-50"
          >
            <Download size={14} />
          </button>

          {/* Email */}
          <button
            onClick={() => setShowEmail(true)}
            title="Enviar por email"
            className="rounded-md border border-gray-200 p-1.5 text-gray-500 hover:bg-gray-50"
          >
            <Mail size={14} />
          </button>

          {/* WhatsApp */}
          <button
            onClick={() =>
              openWhatsApp(`${baseUrl}/whatsapp-link`, customerPhone ?? undefined)
            }
            disabled={isWhatsAppLoading}
            title="Enviar por WhatsApp"
            className="rounded-md border border-green-200 p-1.5 text-green-600 hover:bg-green-50 disabled:opacity-50"
          >
            <MessageCircle size={14} />
          </button>

          {note.status === 'draft' && (
            <>
              <button
                onClick={() => setEditing(true)}
                title="Editar"
                className="rounded-md border border-gray-200 px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
              >
                Editar
              </button>
              <button
                onClick={async () => {
                  try {
                    await issueNote.mutateAsync({
                      workOrderId,
                      deliveryNoteId: note.id,
                    })
                  } catch (e) {
                    alert(getApiErrorMessage(e))
                  }
                }}
                title="Emitir albarán"
                className="rounded-md border border-blue-300 p-1.5 text-blue-600 hover:bg-blue-50"
              >
                <Send size={14} />
              </button>
              <button
                onClick={async () => {
                  if (
                    !confirm(
                      '¿Eliminar este albarán? Esta acción no se puede deshacer.',
                    )
                  )
                    return
                  try {
                    await deleteNote.mutateAsync({
                      workOrderId,
                      deliveryNoteId: note.id,
                    })
                  } catch (e) {
                    alert(getApiErrorMessage(e))
                  }
                }}
                title="Eliminar"
                className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50"
              >
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Lines table */}
      {expanded && note.items.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <div className="hidden grid-cols-[100px_1fr_60px_50px_80px_80px] gap-2 pb-1 text-xs font-medium text-gray-400 sm:grid">
            <span>Tipo</span>
            <span>Descripción</span>
            <span className="text-right">Cant.</span>
            <span>Ud.</span>
            <span className="text-right">P. unit.</span>
            <span className="text-right">Subtotal</span>
          </div>
          <div className="space-y-1">
            {note.items.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-1 gap-x-2 text-sm sm:grid-cols-[100px_1fr_60px_50px_80px_80px] sm:items-center"
              >
                <span className="text-xs text-gray-400">
                  {LINE_TYPE_LABELS[item.line_type]}
                </span>
                <span className="truncate text-gray-700">{item.description}</span>
                <span className="text-right text-gray-600">
                  {Number(item.quantity).toLocaleString('es-ES', {
                    maximumFractionDigits: 3,
                  })}
                </span>
                <span className="text-gray-500">{item.unit}</span>
                <span className="text-right text-gray-600">{fmt(item.unit_price)}</span>
                <span className="text-right font-medium text-gray-800">
                  {fmt(item.subtotal)} €
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-end border-t border-gray-100 pt-2">
            <p className="text-sm font-semibold text-gray-800">
              Total: {fmt(note.total_amount)} €
            </p>
          </div>
        </div>
      )}
    </div>
    </>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface DeliveryNoteListProps {
  workOrder: WorkOrder
  customerEmail?: string | null
  customerPhone?: string | null
}

export function DeliveryNoteList({
  workOrder,
  customerEmail,
  customerPhone,
}: DeliveryNoteListProps) {
  const [showForm, setShowForm] = useState(false)

  return (
    <div className="space-y-4">
      {workOrder.delivery_notes.length === 0 && !showForm && (
        <p className="py-4 text-center text-sm text-gray-400">
          No hay albaranes en esta obra.
        </p>
      )}

      {workOrder.delivery_notes.map((note) => (
        <DeliveryNoteCard
          key={note.id}
          note={note}
          workOrderId={workOrder.id}
          customerEmail={customerEmail}
          customerPhone={customerPhone}
        />
      ))}

      {showForm && (
        <DeliveryNoteForm
          workOrderId={workOrder.id}
          onClose={() => setShowForm(false)}
        />
      )}

      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-3 text-sm text-gray-500 hover:border-gray-400 hover:bg-gray-50"
        >
          <Plus size={14} />
          Nuevo albarán
        </button>
      )}
    </div>
  )
}
