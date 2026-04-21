import type { WorkOrderPreview } from '../types'

interface WorkOrderPreviewModalProps {
  preview: WorkOrderPreview
  isConfirming: boolean
  onConfirm: () => void
  onClose: () => void
}

export function WorkOrderPreviewModal({
  preview,
  isConfirming,
  onConfirm,
  onClose,
}: WorkOrderPreviewModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            Confirmar creación de obra
          </h2>
          <p className="mt-0.5 text-sm text-gray-500">
            Presupuesto <strong>{preview.budget_number}</strong> · {preview.customer_name}
          </p>
        </div>

        {/* Two-column content */}
        <div className="grid grid-cols-2 gap-4 px-6 py-4">
          {/* Tasks */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Tareas a crear ({preview.tasks_to_create.length})
            </h3>
            {preview.tasks_to_create.length === 0 ? (
              <p className="text-sm text-gray-400">
                No hay líneas de mano de obra en este presupuesto.
              </p>
            ) : (
              <div className="space-y-1.5">
                {preview.tasks_to_create.map((t, i) => (
                  <div key={i} className="rounded-md border border-gray-100 px-3 py-2">
                    <div className="text-sm font-medium text-gray-800">{t.name}</div>
                    <div className="text-xs text-gray-500">
                      {t.estimated_hours}h estimadas
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Materials */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Materiales necesarios ({preview.materials_to_reserve.length})
            </h3>
            {preview.materials_to_reserve.length === 0 ? (
              <p className="text-sm text-gray-400">
                No hay líneas de material en este presupuesto.
              </p>
            ) : (
              <div className="space-y-1.5">
                {preview.materials_to_reserve.map((m, i) => (
                  <div
                    key={i}
                    className="rounded-md border border-gray-100 px-3 py-2"
                  >
                    <div className="text-sm font-medium text-gray-800">{m.name}</div>
                    <div className="text-xs text-gray-500">
                      {m.quantity} {m.unit} · Stock actual: {m.stock_available}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Cost total */}
        <div className="border-t border-gray-100 px-6 py-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Coste estimado de la obra:</span>
            <span className="font-semibold text-gray-900">
              {preview.total_estimated_cost.toLocaleString('es-ES', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              €
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-6 py-4 space-y-3">
          <p className="text-xs text-gray-500">
            Esto marcará el presupuesto como aceptado. Esta acción no se puede deshacer.
          </p>
          <div className="flex gap-2 justify-end">
            <button
              onClick={onClose}
              disabled={isConfirming}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              disabled={isConfirming}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isConfirming ? 'Creando obra...' : 'Confirmar y crear obra'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
