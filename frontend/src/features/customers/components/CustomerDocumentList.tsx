import { useRef, useState } from 'react'
import { FileText, Download, Trash2, Upload } from 'lucide-react'
import { useUploadDocument, useDeleteDocument } from '../hooks/use-customers'
import type { CustomerDocument } from '../types'

const DOCUMENT_TYPE_OPTIONS = [
  { value: 'contract', label: 'Contrato' },
  { value: 'id_document', label: 'DNI / CIF' },
  { value: 'authorization', label: 'Autorización' },
  { value: 'other', label: 'Otro' },
]

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  contract: 'Contrato',
  id_document: 'DNI / CIF',
  authorization: 'Autorización',
  other: 'Otro',
}

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

  return (
    <div className="space-y-4">
      {/* Documents list */}
      {documents.length > 0 && (
        <div className="space-y-2">
          {documents.map((doc) => (
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

      {/* Upload zone */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-gray-600">Tipo de documento</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="border border-gray-200 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {DOCUMENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
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
