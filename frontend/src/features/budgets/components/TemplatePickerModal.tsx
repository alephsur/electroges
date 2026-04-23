import { useState } from 'react'
import { X, Search, LayoutTemplate, Loader2 } from 'lucide-react'
import { useBudgetTemplates, useApplyTemplate } from '../hooks/use-budget-templates'
import type { BudgetTemplateSummary } from '../types'

interface TemplatePickerModalProps {
  budgetId: string
  hasExistingLines: boolean
  onClose: () => void
}

type ApplyMode = 'append' | 'replace'

function formatEur(value: number) {
  return Number(value).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function TemplatePickerModal({
  budgetId,
  hasExistingLines,
  onClose,
}: TemplatePickerModalProps) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<BudgetTemplateSummary | null>(null)
  const [mode, setMode] = useState<ApplyMode>(hasExistingLines ? 'append' : 'replace')
  const { data, isLoading } = useBudgetTemplates(query)
  const applyTemplate = useApplyTemplate(budgetId)

  const templates = data?.items ?? []

  const handleApply = () => {
    if (!selected) return
    applyTemplate.mutate(
      { templateId: selected.id, mode },
      { onSuccess: onClose },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <div className="flex items-center gap-2">
            <LayoutTemplate size={18} className="text-indigo-600" />
            <h2 className="text-base font-semibold text-gray-900">Aplicar plantilla</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X size={18} />
          </button>
        </div>

        {/* Search */}
        <div className="px-5 pt-3 pb-2">
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

        {/* List */}
        <div className="flex-1 overflow-y-auto px-5 py-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-10 text-sm text-gray-400">
              <Loader2 size={16} className="animate-spin mr-2" />
              Cargando plantillas...
            </div>
          ) : templates.length === 0 ? (
            <div className="py-10 text-center text-sm text-gray-400">
              {query
                ? 'No se encontraron plantillas que coincidan con la búsqueda'
                : 'No hay plantillas creadas todavía. Puedes crear una desde un presupuesto existente.'}
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {templates.map((tpl) => {
                const isSelected = selected?.id === tpl.id
                return (
                  <li key={tpl.id}>
                    <button
                      onClick={() => setSelected(tpl)}
                      className={`w-full text-left px-3 py-3 rounded-md border transition-colors ${
                        isSelected
                          ? 'border-indigo-300 bg-indigo-50'
                          : 'border-transparent hover:bg-gray-50'
                      }`}
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
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Mode + actions */}
        <div className="border-t border-gray-100 px-5 py-3 space-y-3">
          {hasExistingLines && selected && (
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-gray-600">
                Este presupuesto ya tiene líneas. ¿Qué hacer?
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setMode('append')}
                  className={`flex-1 rounded-md border px-3 py-2 text-xs text-left transition-colors ${
                    mode === 'append'
                      ? 'border-indigo-300 bg-indigo-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-semibold text-gray-900">Añadir</div>
                  <div className="text-gray-500 mt-0.5">
                    Mantiene las líneas actuales y añade las de la plantilla
                  </div>
                </button>
                <button
                  onClick={() => setMode('replace')}
                  className={`flex-1 rounded-md border px-3 py-2 text-xs text-left transition-colors ${
                    mode === 'replace'
                      ? 'border-red-300 bg-red-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-semibold text-gray-900">Reemplazar</div>
                  <div className="text-gray-500 mt-0.5">
                    Elimina las líneas actuales y usa solo las de la plantilla
                  </div>
                </button>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleApply}
              disabled={!selected || applyTemplate.isPending}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {applyTemplate.isPending ? 'Aplicando...' : 'Aplicar plantilla'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
