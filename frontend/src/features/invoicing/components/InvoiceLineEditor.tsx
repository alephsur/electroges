import { useState } from 'react'
import { Plus, Trash2, Save, X } from 'lucide-react'
import {
  useAddInvoiceLine,
  useDeleteInvoiceLine,
  useUpdateInvoiceLine,
} from '../hooks/use-invoice-lines'
import type { InvoiceLine } from '../types'

const ORIGIN_LABEL: Record<string, { label: string; className: string }> = {
  certification: {
    label: 'Certificación',
    className: 'bg-blue-100 text-blue-700',
  },
  task: { label: 'Tarea', className: 'bg-green-100 text-green-700' },
  manual: { label: 'Manual', className: 'bg-gray-100 text-gray-600' },
}

function fmt(n: number) {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

interface EditingLine {
  description: string
  quantity: string
  unit: string
  unit_price: string
  line_discount_pct: string
}

interface Props {
  invoiceId: string
  lines: InvoiceLine[]
  isEditable: boolean
}

export function InvoiceLineEditor({ invoiceId, lines, isEditable }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<EditingLine | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newLine, setNewLine] = useState<EditingLine>({
    description: '',
    quantity: '1',
    unit: '',
    unit_price: '0',
    line_discount_pct: '0',
  })

  const { mutate: updateLine, isPending: isUpdating } =
    useUpdateInvoiceLine(invoiceId)
  const { mutate: deleteLine } = useDeleteInvoiceLine(invoiceId)
  const { mutate: addLine, isPending: isAdding } = useAddInvoiceLine(invoiceId)

  function startEdit(line: InvoiceLine) {
    setEditingId(line.id)
    setEditValues({
      description: line.description,
      quantity: String(line.quantity),
      unit: line.unit ?? '',
      unit_price: String(line.unit_price),
      line_discount_pct: String(line.line_discount_pct),
    })
  }

  function saveEdit(lineId: string) {
    if (!editValues) return
    updateLine(
      {
        lineId,
        description: editValues.description,
        quantity: parseFloat(editValues.quantity),
        unit: editValues.unit || null,
        unit_price: parseFloat(editValues.unit_price),
        line_discount_pct: parseFloat(editValues.line_discount_pct),
      },
      {
        onSuccess: () => {
          setEditingId(null)
          setEditValues(null)
        },
      },
    )
  }

  function handleAddLine() {
    addLine(
      {
        origin_type: 'manual',
        description: newLine.description,
        quantity: parseFloat(newLine.quantity),
        unit: newLine.unit || null,
        unit_price: parseFloat(newLine.unit_price),
        line_discount_pct: parseFloat(newLine.line_discount_pct),
      },
      {
        onSuccess: () => {
          setShowAddForm(false)
          setNewLine({
            description: '',
            quantity: '1',
            unit: '',
            unit_price: '0',
            line_discount_pct: '0',
          })
        },
      },
    )
  }

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs text-gray-500">
            <th className="pb-2 text-left font-medium">Descripción</th>
            <th className="pb-2 text-right font-medium">Cant.</th>
            <th className="pb-2 text-right font-medium">P. unit.</th>
            <th className="pb-2 text-right font-medium">Dto.</th>
            <th className="pb-2 text-right font-medium">Importe</th>
            {isEditable && <th className="pb-2"></th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {lines.map((line) =>
            editingId === line.id && editValues ? (
              <tr key={line.id} className="bg-blue-50">
                <td className="py-2 pr-2">
                  <input
                    value={editValues.description}
                    onChange={(e) =>
                      setEditValues((v) => v && { ...v, description: e.target.value })
                    }
                    className="w-full rounded border border-blue-300 px-2 py-1 text-xs"
                  />
                </td>
                <td className="py-2 pr-2 text-right">
                  <input
                    type="number"
                    value={editValues.quantity}
                    onChange={(e) =>
                      setEditValues((v) => v && { ...v, quantity: e.target.value })
                    }
                    className="w-16 rounded border border-blue-300 px-2 py-1 text-right text-xs"
                  />
                </td>
                <td className="py-2 pr-2 text-right">
                  <input
                    type="number"
                    value={editValues.unit_price}
                    onChange={(e) =>
                      setEditValues((v) => v && { ...v, unit_price: e.target.value })
                    }
                    className="w-20 rounded border border-blue-300 px-2 py-1 text-right text-xs"
                  />
                </td>
                <td className="py-2 pr-2 text-right">
                  <input
                    type="number"
                    value={editValues.line_discount_pct}
                    onChange={(e) =>
                      setEditValues((v) => v && { ...v, line_discount_pct: e.target.value })
                    }
                    className="w-12 rounded border border-blue-300 px-2 py-1 text-right text-xs"
                  />
                </td>
                <td className="py-2 pr-2 text-right text-xs text-gray-500">—</td>
                <td className="py-2 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => saveEdit(line.id)}
                      disabled={isUpdating}
                      className="rounded p-1 text-green-600 hover:bg-green-50"
                    >
                      <Save size={12} />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100"
                    >
                      <X size={12} />
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr
                key={line.id}
                className="group hover:bg-gray-50"
                onDoubleClick={() => isEditable && startEdit(line)}
              >
                <td className="py-2 pr-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${ORIGIN_LABEL[line.origin_type]?.className ?? 'bg-gray-100'}`}
                    >
                      {ORIGIN_LABEL[line.origin_type]?.label ?? line.origin_type}
                    </span>
                    <span className="text-gray-800">{line.description}</span>
                  </div>
                </td>
                <td className="py-2 pr-2 text-right text-gray-600">
                  {line.quantity}
                  {line.unit && (
                    <span className="ml-1 text-xs text-gray-400">
                      {line.unit}
                    </span>
                  )}
                </td>
                <td className="py-2 pr-2 text-right text-gray-600">
                  {fmt(line.unit_price)} €
                </td>
                <td className="py-2 pr-2 text-right text-gray-500 text-xs">
                  {line.line_discount_pct > 0 ? `${line.line_discount_pct}%` : '—'}
                </td>
                <td className="py-2 pr-2 text-right font-medium text-gray-800">
                  {fmt(line.subtotal)} €
                </td>
                {isEditable && (
                  <td className="py-2 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100">
                      <button
                        onClick={() => startEdit(line)}
                        className="rounded p-1 text-blue-500 hover:bg-blue-50"
                        title="Editar"
                      >
                        ✎
                      </button>
                      <button
                        onClick={() => deleteLine(line.id)}
                        className="rounded p-1 text-red-400 hover:bg-red-50"
                        title="Eliminar"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ),
          )}
        </tbody>
      </table>

      {isEditable && (
        <>
          {showAddForm ? (
            <div className="mt-3 rounded border border-dashed border-blue-300 bg-blue-50 p-3">
              <div className="grid grid-cols-5 gap-2">
                <div className="col-span-2">
                  <input
                    placeholder="Descripción"
                    value={newLine.description}
                    onChange={(e) =>
                      setNewLine((v) => ({ ...v, description: e.target.value }))
                    }
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  />
                </div>
                <input
                  type="number"
                  placeholder="Cant."
                  value={newLine.quantity}
                  onChange={(e) =>
                    setNewLine((v) => ({ ...v, quantity: e.target.value }))
                  }
                  className="rounded border border-gray-300 px-2 py-1 text-right text-xs"
                />
                <input
                  type="number"
                  placeholder="P. unit."
                  value={newLine.unit_price}
                  onChange={(e) =>
                    setNewLine((v) => ({ ...v, unit_price: e.target.value }))
                  }
                  className="rounded border border-gray-300 px-2 py-1 text-right text-xs"
                />
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleAddLine}
                    disabled={isAdding || !newLine.description}
                    className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-40"
                  >
                    <Save size={12} />
                  </button>
                  <button
                    onClick={() => setShowAddForm(false)}
                    className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowAddForm(true)}
              className="mt-3 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
            >
              <Plus size={12} /> Añadir línea manual
            </button>
          )}
        </>
      )}
    </div>
  )
}
