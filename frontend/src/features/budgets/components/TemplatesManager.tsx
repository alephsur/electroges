import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  LayoutTemplate,
  Search,
  Edit2,
  Trash2,
  Check,
  X,
  Loader2,
  FolderOpen,
  FileText,
} from 'lucide-react'
import {
  useBudgetTemplates,
  useBudgetTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from '../hooks/use-budget-templates'
import type { BudgetTemplateSummary } from '../types'

function formatEur(value: number) {
  return Number(value).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const LINE_TYPE_LABELS: Record<string, string> = {
  labor: 'Mano de obra',
  material: 'Material',
  other: 'Partida',
}

const LINE_TYPE_CLASSES: Record<string, string> = {
  labor: 'bg-blue-100 text-blue-700',
  material: 'bg-green-100 text-green-700',
  other: 'bg-gray-100 text-gray-600',
}

// ── Edit row (inline name/description edit) ──────────────────────────────────

interface EditRowProps {
  template: BudgetTemplateSummary
  onDone: () => void
}

function EditRow({ template, onDone }: EditRowProps) {
  const [name, setName] = useState(template.name)
  const [description, setDescription] = useState(template.description ?? '')
  const updateTemplate = useUpdateTemplate()

  const handleSave = () => {
    if (!name.trim()) return
    updateTemplate.mutate(
      {
        id: template.id,
        name: name.trim(),
        description: description.trim() || null,
      },
      { onSuccess: onDone },
    )
  }

  return (
    <div className="rounded-md border border-indigo-200 bg-indigo-50 p-3 space-y-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
        autoFocus
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Descripción (opcional)"
        rows={2}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
      <div className="flex justify-end gap-1">
        <button
          onClick={handleSave}
          disabled={!name.trim() || updateTemplate.isPending}
          className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Check size={13} />
        </button>
        <button
          onClick={onDone}
          className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}

// ── Template detail panel ─────────────────────────────────────────────────────

function TemplateDetailPanel({ templateId }: { templateId: string }) {
  const { data: template, isLoading } = useBudgetTemplate(templateId)

  if (isLoading || !template) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-gray-400">
        <Loader2 size={16} className="animate-spin mr-2" />
        Cargando...
      </div>
    )
  }

  const sectionsSorted = [...template.sections].sort(
    (a, b) => a.sort_order - b.sort_order,
  )
  const linesBySection = new Map<string | null, typeof template.lines>()
  for (const line of template.lines) {
    const key = line.section_id ?? null
    const arr = linesBySection.get(key) ?? []
    arr.push(line)
    linesBySection.set(key, arr)
  }
  for (const [k, arr] of linesBySection.entries()) {
    arr.sort((a, b) => a.sort_order - b.sort_order)
    linesBySection.set(k, arr)
  }
  const unsectioned = linesBySection.get(null) ?? []

  return (
    <div className="space-y-3">
      {sectionsSorted.map((section) => {
        const lines = linesBySection.get(section.id) ?? []
        return (
          <div key={section.id} className="rounded-md border border-gray-200">
            <div className="bg-indigo-50 px-3 py-2 border-b border-indigo-100 flex items-center gap-2">
              <FolderOpen size={14} className="text-indigo-700" />
              <span className="font-semibold text-indigo-900 text-sm">
                {section.name}
              </span>
              {section.notes && (
                <span className="text-xs text-indigo-600">· {section.notes}</span>
              )}
            </div>
            {lines.length === 0 ? (
              <div className="px-3 py-2 text-xs text-gray-400 italic">
                Sin líneas
              </div>
            ) : (
              <table className="w-full text-xs">
                <tbody className="divide-y divide-gray-100">
                  {lines.map((line) => (
                    <tr key={line.id}>
                      <td className="px-3 py-1.5">
                        <span
                          className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                            LINE_TYPE_CLASSES[line.line_type]
                          }`}
                        >
                          {LINE_TYPE_LABELS[line.line_type]}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-gray-800">
                        {line.description}
                      </td>
                      <td className="px-3 py-1.5 text-right text-gray-500">
                        {line.quantity} {line.unit ?? ''}
                      </td>
                      <td className="px-3 py-1.5 text-right text-gray-600">
                        {formatEur(line.unit_price)} €
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )
      })}

      {unsectioned.length > 0 && (
        <div className="rounded-md border border-gray-200">
          <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 flex items-center gap-2">
            <FileText size={14} className="text-gray-500" />
            <span className="font-semibold text-gray-700 text-sm">Sin capítulo</span>
          </div>
          <table className="w-full text-xs">
            <tbody className="divide-y divide-gray-100">
              {unsectioned.map((line) => (
                <tr key={line.id}>
                  <td className="px-3 py-1.5">
                    <span
                      className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                        LINE_TYPE_CLASSES[line.line_type]
                      }`}
                    >
                      {LINE_TYPE_LABELS[line.line_type]}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-gray-800">{line.description}</td>
                  <td className="px-3 py-1.5 text-right text-gray-500">
                    {line.quantity} {line.unit ?? ''}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-600">
                    {formatEur(line.unit_price)} €
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {template.sections.length === 0 && template.lines.length === 0 && (
        <div className="py-8 text-center text-sm text-gray-400">
          Esta plantilla no contiene líneas
        </div>
      )}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export function TemplatesManager() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  const { data, isLoading } = useBudgetTemplates(query)
  const deleteTemplate = useDeleteTemplate()
  const templates = data?.items ?? []

  const selected = templates.find((t) => t.id === selectedId) ?? null

  const handleDelete = (id: string) => {
    deleteTemplate.mutate(id, {
      onSuccess: () => {
        setConfirmDeleteId(null)
        if (selectedId === id) setSelectedId(null)
      },
    })
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: list */}
      <div className="flex flex-col border-r border-gray-100 w-full lg:w-[45%] lg:shrink-0">
        <div className="shrink-0 border-b border-gray-100 p-4">
          <button
            onClick={() => navigate('/presupuestos')}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 mb-2"
          >
            <ArrowLeft size={13} />
            Volver a presupuestos
          </button>
          <div className="flex items-center gap-2 mb-3">
            <LayoutTemplate size={18} className="text-indigo-600" />
            <h1 className="text-lg font-semibold text-gray-900">Plantillas</h1>
            {data && (
              <span className="text-sm text-gray-400">({data.total})</span>
            )}
          </div>
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar plantilla..."
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-10 text-sm text-gray-400">
              <Loader2 size={16} className="animate-spin mr-2" />
              Cargando...
            </div>
          ) : templates.length === 0 ? (
            <div className="py-10 text-center text-sm text-gray-400">
              {query
                ? 'No se encontraron plantillas'
                : 'Aún no hay plantillas. Crea una desde un presupuesto usando "Guardar como plantilla".'}
            </div>
          ) : (
            <ul className="space-y-2">
              {templates.map((tpl) => {
                if (editingId === tpl.id) {
                  return (
                    <li key={tpl.id}>
                      <EditRow template={tpl} onDone={() => setEditingId(null)} />
                    </li>
                  )
                }
                const isSelected = selectedId === tpl.id
                return (
                  <li key={tpl.id}>
                    <div
                      className={`rounded-md border transition-colors ${
                        isSelected
                          ? 'border-indigo-300 bg-indigo-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <button
                        onClick={() => setSelectedId(tpl.id)}
                        className="w-full text-left px-3 py-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-semibold text-gray-900">
                              {tpl.name}
                            </div>
                            {tpl.description && (
                              <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                                {tpl.description}
                              </div>
                            )}
                            <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                              <span>{tpl.sections_count} capítulos</span>
                              <span>·</span>
                              <span>{tpl.lines_count} líneas</span>
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="text-sm font-bold text-gray-900">
                              {formatEur(tpl.estimated_total)} €
                            </div>
                            <div className="text-[10px] text-gray-400">estimado</div>
                          </div>
                        </div>
                      </button>
                      <div className="flex justify-end gap-1 border-t border-gray-100 px-2 py-1.5">
                        <button
                          onClick={() => setEditingId(tpl.id)}
                          className="flex items-center gap-1 rounded px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
                        >
                          <Edit2 size={11} />
                          Renombrar
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(tpl.id)}
                          className="flex items-center gap-1 rounded px-2 py-0.5 text-xs text-red-600 hover:bg-red-50"
                        >
                          <Trash2 size={11} />
                          Eliminar
                        </button>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Right: detail */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {selected ? (
          <>
            <div className="shrink-0 border-b border-gray-100 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold text-gray-900">
                    {selected.name}
                  </h2>
                  {selected.description && (
                    <p className="text-xs text-gray-500 mt-1">
                      {selected.description}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="text-lg font-bold text-gray-900">
                    {formatEur(selected.estimated_total)} €
                  </div>
                  <div className="text-xs text-gray-400">
                    {selected.sections_count} capítulos · {selected.lines_count} líneas
                  </div>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <TemplateDetailPanel templateId={selected.id} />
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            Selecciona una plantilla para ver el detalle
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white shadow-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                <Trash2 size={18} className="text-red-600" />
              </div>
              <h3 className="text-sm font-semibold text-gray-900">
                Eliminar plantilla
              </h3>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              Esta acción es permanente y no se puede deshacer. Los presupuestos que
              hayan usado esta plantilla no se verán afectados.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmDeleteId(null)}
                disabled={deleteTemplate.isPending}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleDelete(confirmDeleteId)}
                disabled={deleteTemplate.isPending}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteTemplate.isPending ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
