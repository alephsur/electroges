import { useRef } from 'react'
import { Download, FileText, Trash2, Upload } from 'lucide-react'
import type { SiteVisit } from '../types'
import { useDeleteDocument, useUploadDocument } from '../hooks/use-site-visit-documents'

const DOC_TYPE_LABELS: Record<string, string> = {
  sketch: 'Croquis',
  plan: 'Plano',
  authorization: 'Autorización',
  other: 'Otro',
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface SiteVisitDocumentListProps {
  visit: SiteVisit
}

export function SiteVisitDocumentList({ visit }: SiteVisitDocumentListProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadDoc = useUploadDocument(visit.id)
  const deleteDoc = useDeleteDocument(visit.id)
  const isEditable = visit.status === 'scheduled' || visit.status === 'in_progress'
  const documents = visit.documents

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    Array.from(files).forEach((file) => uploadDoc.mutate({ file, documentType: 'other' }))
    e.target.value = ''
  }

  return (
    <div className="space-y-3">
      {documents.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-400">Sin documentos adjuntos</p>
      ) : (
        <div className="divide-y divide-gray-100">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center gap-3 py-3">
              <FileText size={18} className="shrink-0 text-gray-400" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">{doc.name}</p>
                <p className="text-xs text-gray-400">
                  {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
                  {doc.file_size_bytes
                    ? ` · ${formatFileSize(doc.file_size_bytes)}`
                    : ''}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <a
                  href={doc.file_path}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded p-1 text-gray-400 hover:text-blue-600"
                  title="Descargar"
                >
                  <Download size={14} />
                </a>
                {isEditable && (
                  <button
                    onClick={() => deleteDoc.mutate(doc.id)}
                    disabled={deleteDoc.isPending}
                    className="rounded p-1 text-gray-400 hover:text-red-600 disabled:opacity-50"
                    title="Eliminar"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {isEditable && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDoc.isPending}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            <Upload size={14} />
            {uploadDoc.isPending ? 'Subiendo...' : 'Adjuntar documento'}
          </button>
        </>
      )}
    </div>
  )
}
