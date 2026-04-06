import { Camera, FileText, MapPin, Package } from 'lucide-react'
import { useNavigate, useMatch } from 'react-router-dom'
import type { SiteVisitSummary } from '../types'
import { SiteVisitStatusBadge } from './SiteVisitStatusBadge'

function formatVisitDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Hoy'
  if (diffDays === 1) return 'Mañana'
  if (diffDays > 1 && diffDays <= 7) return `En ${diffDays} días`

  return date.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface SiteVisitListProps {
  visits: SiteVisitSummary[]
  isLoading?: boolean
}

export function SiteVisitList({ visits, isLoading }: SiteVisitListProps) {
  const navigate = useNavigate()
  const match = useMatch('/visitas/:visitId')
  const selectedVisitId = match?.params.visitId ?? null

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-gray-400">
        Cargando visitas...
      </div>
    )
  }

  if (visits.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-gray-400">
        <MapPin size={36} className="mb-3 text-gray-300" />
        <p className="font-medium text-gray-500">Sin visitas técnicas</p>
        <p className="mt-1 text-sm">Crea una nueva visita para empezar</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-100">
      {visits.map((visit) => (
        <div
          key={visit.id}
          onClick={() => navigate(`/visitas/${visit.id}`)}
          className={`cursor-pointer p-4 transition-colors hover:bg-gray-50 ${
            selectedVisitId === visit.id
              ? 'border-l-2 border-blue-600 bg-blue-50'
              : ''
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              {/* Customer / contact */}
              <div className="mb-1 flex items-center gap-2 flex-wrap">
                {visit.customer_name ? (
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {visit.customer_name}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-sm text-gray-400">
                    <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-500">
                      ?
                    </span>
                    Sin cliente
                  </span>
                )}
                {visit.contact_name && !visit.customer_name && (
                  <span className="text-xs text-gray-500">{visit.contact_name}</span>
                )}
              </div>

              {/* Address */}
              <div className="mb-2 flex items-center gap-1.5 text-xs text-gray-500">
                <MapPin size={11} className="shrink-0" />
                <span className="truncate">{visit.address_display}</span>
              </div>

              {/* Icons row */}
              <div className="flex items-center gap-3 text-xs text-gray-400">
                {visit.materials_count > 0 && (
                  <span className="flex items-center gap-1">
                    <Package size={11} />
                    {visit.materials_count}
                  </span>
                )}
                {visit.has_photos && (
                  <span className="flex items-center gap-1">
                    <Camera size={11} />
                    Fotos
                  </span>
                )}
                {visit.has_documents && (
                  <span className="flex items-center gap-1">
                    <FileText size={11} />
                    Docs
                  </span>
                )}
                {visit.estimated_budget != null && (
                  <span className="text-gray-300">
                    ~
                    {visit.estimated_budget.toLocaleString('es-ES', {
                      minimumFractionDigits: 0,
                    })}{' '}
                    €
                  </span>
                )}
              </div>
            </div>

            {/* Right side */}
            <div className="flex shrink-0 flex-col items-end gap-2">
              <SiteVisitStatusBadge status={visit.status} />
              <span className="text-xs text-gray-400">{formatVisitDate(visit.visit_date)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
