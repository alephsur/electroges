import { useState } from 'react'
import { X, Save } from 'lucide-react'
import { useSaveBudgetAsTemplate } from '../hooks/use-budget-templates'

interface SaveAsTemplateModalProps {
  budgetId: string
  budgetNumber: string
  onClose: () => void
}

export function SaveAsTemplateModal({
  budgetId,
  budgetNumber,
  onClose,
}: SaveAsTemplateModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const saveAsTemplate = useSaveBudgetAsTemplate()

  const handleSave = () => {
    if (!name.trim()) return
    saveAsTemplate.mutate(
      {
        budgetId,
        name: name.trim(),
        description: description.trim() || undefined,
      },
      { onSuccess: onClose },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <div className="flex items-center gap-2">
            <Save size={18} className="text-indigo-600" />
            <h2 className="text-base font-semibold text-gray-900">
              Guardar como plantilla
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-gray-600">
            Se creará una plantilla reutilizable a partir de las líneas y capítulos del
            presupuesto <strong>{budgetNumber}</strong>.
          </p>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Nombre de la plantilla <span className="text-red-500">*</span>
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Instalación base vivienda 90m²"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Descripción (opcional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descripción breve del uso de la plantilla..."
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {saveAsTemplate.isError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {(saveAsTemplate.error as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail ?? 'No se pudo crear la plantilla'}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-100 px-5 py-3">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saveAsTemplate.isPending}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saveAsTemplate.isPending ? 'Guardando...' : 'Guardar plantilla'}
          </button>
        </div>
      </div>
    </div>
  )
}
