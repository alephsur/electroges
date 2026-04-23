import { useRef, useState } from 'react'
import {
  X,
  Upload,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Download,
} from 'lucide-react'
import { usePreviewImport, useConfirmImport } from '../hooks/use-budget-import'
import type { ImportPreview, BudgetLineType } from '../types'

interface ImportLinesModalProps {
  budgetId: string
  onClose: () => void
}

const LINE_TYPE_LABELS: Record<BudgetLineType, string> = {
  labor: 'Mano de obra',
  material: 'Material',
  other: 'Partida',
}

const LINE_TYPE_CLASSES: Record<BudgetLineType, string> = {
  labor: 'bg-blue-100 text-blue-700',
  material: 'bg-green-100 text-green-700',
  other: 'bg-gray-100 text-gray-600',
}

const CSV_TEMPLATE = [
  'capitulo,tipo,descripcion,cantidad,unidad,precio_unitario,coste_unitario,descuento_porcentaje',
  'Cuadro eléctrico,material,Cuadro general 12 módulos,1,ud,85.00,55.00,0',
  'Cuadro eléctrico,labor,Instalación cuadro general,2,h,35.00,20.00,0',
  'Distribución interior,material,Cable unipolar 2.5mm²,100,m,0.85,0.55,0',
  'Distribución interior,labor,Tendido de cable y cajeado,6,h,35.00,20.00,0',
].join('\n')

function downloadCsvTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'plantilla_importacion_presupuesto.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function formatEur(value: number) {
  return Number(value).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function ImportLinesModal({ budgetId, onClose }: ImportLinesModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const previewMutation = usePreviewImport(budgetId)
  const confirmMutation = useConfirmImport(budgetId)

  const handleFileChange = async (selected: File | null) => {
    setPreview(null)
    setFile(selected)
    if (!selected) return
    try {
      const result = await previewMutation.mutateAsync(selected)
      setPreview(result)
    } catch {
      setPreview(null)
    }
  }

  const handleConfirm = () => {
    if (!preview || preview.valid_rows.length === 0) return
    confirmMutation.mutate(preview.valid_rows, {
      onSuccess: () => {
        setConfirmed(true)
        setTimeout(() => onClose(), 800)
      },
    })
  }

  const validCount = preview?.valid_rows.length ?? 0
  const errorCount = preview?.errors.length ?? 0
  const canConfirm = validCount > 0 && !confirmMutation.isPending && !confirmed

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-4xl rounded-xl bg-white shadow-xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3 shrink-0">
          <div className="flex items-center gap-2">
            <FileSpreadsheet size={18} className="text-purple-600" />
            <h2 className="text-base font-semibold text-gray-900">
              Importar líneas desde CSV/Excel
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Upload zone */}
          {!preview && (
            <div className="space-y-4">
              <div className="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs text-blue-800">
                <div className="font-semibold mb-1">Formato esperado</div>
                <div>
                  Columnas reconocidas: <code className="bg-white px-1 rounded">capitulo</code>,{' '}
                  <code className="bg-white px-1 rounded">tipo</code> (labor/material/otro),{' '}
                  <code className="bg-white px-1 rounded">descripcion</code>,{' '}
                  <code className="bg-white px-1 rounded">cantidad</code>,{' '}
                  <code className="bg-white px-1 rounded">unidad</code>,{' '}
                  <code className="bg-white px-1 rounded">precio_unitario</code>,{' '}
                  <code className="bg-white px-1 rounded">coste_unitario</code>,{' '}
                  <code className="bg-white px-1 rounded">descuento_porcentaje</code>
                </div>
                <button
                  onClick={downloadCsvTemplate}
                  className="mt-2 flex items-center gap-1 text-blue-700 hover:text-blue-900 underline"
                >
                  <Download size={11} />
                  Descargar plantilla CSV de ejemplo
                </button>
              </div>

              <label
                htmlFor="import-file-input"
                className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 py-10 px-4 cursor-pointer hover:border-purple-400 hover:bg-purple-50 transition-colors"
              >
                <Upload size={28} className="text-gray-400 mb-2" />
                <div className="text-sm font-medium text-gray-700">
                  Selecciona un archivo CSV o Excel
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Formatos: .csv, .xlsx, .xls
                </div>
                <input
                  id="import-file-input"
                  ref={inputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                  className="hidden"
                />
              </label>

              {previewMutation.isPending && (
                <div className="flex items-center justify-center py-6 text-sm text-gray-500">
                  <Loader2 size={16} className="animate-spin mr-2" />
                  Procesando archivo...
                </div>
              )}

              {previewMutation.isError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {(previewMutation.error as { response?: { data?: { detail?: string } } })
                    ?.response?.data?.detail ?? 'No se pudo procesar el archivo'}
                </div>
              )}
            </div>
          )}

          {/* Preview */}
          {preview && !confirmed && (
            <div className="space-y-3">
              {/* Summary */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs text-gray-700">
                  <FileSpreadsheet size={13} />
                  {file?.name}
                </div>
                <div className="flex items-center gap-1.5 rounded-md bg-green-100 px-3 py-1.5 text-xs text-green-700">
                  <CheckCircle2 size={13} />
                  {validCount} líneas válidas
                </div>
                {errorCount > 0 && (
                  <div className="flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs text-red-700">
                    <AlertTriangle size={13} />
                    {errorCount} {errorCount === 1 ? 'error' : 'errores'}
                  </div>
                )}
                {preview.sections_detected.length > 0 && (
                  <div className="flex items-center gap-1.5 rounded-md bg-indigo-100 px-3 py-1.5 text-xs text-indigo-700">
                    {preview.sections_detected.length}{' '}
                    {preview.sections_detected.length === 1 ? 'capítulo' : 'capítulos'} detectados
                  </div>
                )}
                <button
                  onClick={() => {
                    setFile(null)
                    setPreview(null)
                    if (inputRef.current) inputRef.current.value = ''
                  }}
                  className="ml-auto text-xs text-gray-500 underline hover:text-gray-700"
                >
                  Cambiar archivo
                </button>
              </div>

              {/* Errors */}
              {errorCount > 0 && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-red-800 mb-1.5">
                    <AlertTriangle size={14} />
                    Filas con errores (no se importarán)
                  </div>
                  <ul className="space-y-0.5 text-xs text-red-700 max-h-32 overflow-y-auto">
                    {preview.errors.map((err, idx) => (
                      <li key={idx}>
                        <span className="font-medium">Fila {err.row_number}</span>
                        {err.field && <span className="text-red-500"> · {err.field}</span>}
                        : {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sections detected */}
              {preview.sections_detected.length > 0 && (
                <div className="rounded-md border border-indigo-100 bg-indigo-50 p-3 text-xs text-indigo-800">
                  <div className="font-semibold mb-1">Capítulos detectados:</div>
                  <div className="flex flex-wrap gap-1">
                    {preview.sections_detected.map((name) => (
                      <span
                        key={name}
                        className="rounded-full bg-white px-2 py-0.5 border border-indigo-200"
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                  <div className="mt-1.5 text-indigo-600">
                    Los capítulos que no existan en el presupuesto se crearán automáticamente.
                  </div>
                </div>
              )}

              {/* Valid rows preview */}
              {validCount > 0 && (
                <div className="rounded-md border border-gray-200 overflow-hidden">
                  <div className="bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-700 border-b border-gray-200">
                    Vista previa de líneas válidas
                  </div>
                  <div className="overflow-x-auto max-h-[40vh] overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-white sticky top-0 border-b border-gray-200">
                        <tr className="text-gray-500">
                          <th className="text-left font-medium px-3 py-2">Capítulo</th>
                          <th className="text-left font-medium px-3 py-2">Tipo</th>
                          <th className="text-left font-medium px-3 py-2">Descripción</th>
                          <th className="text-right font-medium px-3 py-2">Cant.</th>
                          <th className="text-right font-medium px-3 py-2">Ud.</th>
                          <th className="text-right font-medium px-3 py-2">P. unit.</th>
                          <th className="text-right font-medium px-3 py-2">Coste</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {preview.valid_rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-3 py-1.5 text-gray-600">
                              {row.section ?? <span className="text-gray-400">—</span>}
                            </td>
                            <td className="px-3 py-1.5">
                              <span
                                className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                                  LINE_TYPE_CLASSES[row.line_type]
                                }`}
                              >
                                {LINE_TYPE_LABELS[row.line_type]}
                              </span>
                            </td>
                            <td className="px-3 py-1.5 text-gray-800">
                              {row.description}
                            </td>
                            <td className="px-3 py-1.5 text-right text-gray-600">
                              {row.quantity}
                            </td>
                            <td className="px-3 py-1.5 text-right text-gray-500">
                              {row.unit ?? ''}
                            </td>
                            <td className="px-3 py-1.5 text-right text-gray-600">
                              {formatEur(row.unit_price)}
                            </td>
                            <td className="px-3 py-1.5 text-right text-amber-700">
                              {formatEur(row.unit_cost)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {confirmMutation.isError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {(confirmMutation.error as { response?: { data?: { detail?: string } } })
                    ?.response?.data?.detail ?? 'No se pudieron importar las líneas'}
                </div>
              )}
            </div>
          )}

          {confirmed && (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <CheckCircle2 size={40} className="text-green-600 mb-2" />
              <div className="text-sm font-medium text-gray-900">
                {validCount} líneas importadas correctamente
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {preview && !confirmed && (
          <div className="flex justify-end gap-2 border-t border-gray-100 px-5 py-3 shrink-0">
            <button
              onClick={onClose}
              disabled={confirmMutation.isPending}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canConfirm}
              className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            >
              {confirmMutation.isPending
                ? 'Importando...'
                : `Importar ${validCount} ${validCount === 1 ? 'línea' : 'líneas'}`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
