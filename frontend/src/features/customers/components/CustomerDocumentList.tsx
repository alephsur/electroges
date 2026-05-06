import { useRef, useState } from 'react'
import { FileText, Download, Trash2, Upload, Filter } from 'lucide-react'
import { useUploadDocument, useDeleteDocument } from '../hooks/use-customers'
import type { CustomerDocument } from '../types'

const DOCUMENT_TYPE_OPTIONS: { value: string; label: string; group: string }[] = [
  { value: 'contract', label: 'Contrato', group: 'General' },
  { value: 'id_document', label: 'DNI / CIF', group: 'General' },
  { value: 'authorization', label: 'Autorización', group: 'General' },
  { value: 'other', label: 'Otro', group: 'General' },
  { value: 'ci_bt', label: 'Certificado de Instalación BT (CI-BT)', group: 'Documentación eléctrica' },
  { value: 'mtd_bt', label: 'Memoria Técnica de Diseño BT (MTD-BT)', group: 'Documentación eléctrica' },
  { value: 'dr_ttc', label: 'Declaración Responsable (DR-TTC)', group: 'Documentación eléctrica' },
  { value: 'cert_fin_obra', label: 'Certificado de Fin de Obra', group: 'Documentación eléctrica' },
  { value: 'sol_iebt', label: 'Solicitud de Inspección (SOL-IEBT)', group: 'Documentación eléctrica' },
]

const DOCUMENT_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  DOCUMENT_TYPE_OPTIONS.map((o) => [o.value, o.label]),
)

function formatFileSize(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface CustomerDocumentListProps {
  customerId: string
  documents: CustomerDocument[]
}

export function CustomerDocumentList({ customerId, documents }: CustomerDocumentListProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedType, setSelectedType] = useState('other')
  const [filterType, setFilterType] = useState<string>('all')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadDocument = useUploadDocument(customerId)
  const deleteDocument = useDeleteDocument(customerId)

  const handleFile = (file: File) => {
    uploadDocument.mutate({ file, documentType: selectedType })
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const filteredDocuments =
    filterType === 'all' ? documents : documents.filter((d) => d.document_type === filterType)

  const groups = Array.from(new Set(DOCUMENT_TYPE_OPTIONS.map((o) => o.group)))

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      {documents.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter size={13} className="text-gray-400 shrink-0" />
          <button
            onClick={() => setFilterType('all')}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filterType === 'all'
                ? 'bg-brand-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Todos ({documents.length})
          </button>
          {DOCUMENT_TYPE_OPTIONS.filter((opt) =>
            documents.some((d) => d.document_type === opt.value),
          ).map((opt) => {
            const count = documents.filter((d) => d.document_type === opt.value).length
            return (
              <button
                key={opt.value}
                onClick={() => setFilterType(opt.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filterType === opt.value
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label} ({count})
              </button>
            )
          })}
        </div>
      )}

      {/* Documents list */}
      {filteredDocuments.length > 0 && (
        <div className="space-y-2">
          {filteredDocuments.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 border border-gray-200 rounded-lg p-3 bg-white"
            >
              <FileText size={18} className="text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                <p className="text-xs text-gray-400">
                  {DOCUMENT_TYPE_LABELS[doc.document_type] ?? 'Otro'} ·{' '}
                  {formatFileSize(doc.file_size_bytes)} ·{' '}
                  {new Date(doc.created_at).toLocaleDateString('es-ES')}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <a
                  href={`/api/v1/uploads/${doc.file_path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Descargar"
                  className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"
                >
                  <Download size={14} />
                </a>
                <button
                  onClick={() => {
                    if (confirm(`¿Eliminar el documento "${doc.name}"?`))
                      deleteDocument.mutate(doc.id)
                  }}
                  title="Eliminar"
                  className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredDocuments.length === 0 && documents.length > 0 && (
        <p className="text-sm text-gray-400 text-center py-4">
          No hay documentos de este tipo.
        </p>
      )}

      {/* Upload zone */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-gray-600 shrink-0">Tipo de documento</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="border border-gray-200 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {groups.map((group) => (
              <optgroup key={group} label={group}>
                {DOCUMENT_TYPE_OPTIONS.filter((o) => o.group === group).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragging ? 'border-brand-400 bg-brand-50' : 'border-gray-200 bg-gray-50'
          }`}
        >
          <Upload size={20} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-500">
            Arrastra un archivo aquí o{' '}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-brand-600 font-medium hover:underline"
            >
              selecciona uno
            </button>
          </p>
          <p className="text-xs text-gray-400 mt-1">Máximo 10 MB</p>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleFile(file)
              e.target.value = ''
            }}
          />
        </div>

        {uploadDocument.isPending && (
          <p className="text-xs text-gray-500">Subiendo documento...</p>
        )}
      </div>
    </div>
  )
}
