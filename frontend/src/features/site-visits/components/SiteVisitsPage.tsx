import { useEffect, useState } from 'react'
import { Routes, Route, useMatch, useParams } from 'react-router-dom'
import { MapPin, Plus, Search } from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { useSiteVisitStore } from '../store/site-visit-store'
import { useSiteVisit, useSiteVisits } from '../hooks/use-site-visits'
import { SiteVisitList } from './SiteVisitList'
import { SiteVisitDetail } from './SiteVisitDetail'
import { SiteVisitForm } from './SiteVisitForm'
import type { SiteVisitStatus } from '../types'

const STATUS_OPTIONS: { value: SiteVisitStatus; label: string }[] = [
  { value: 'scheduled', label: 'Planificadas' },
  { value: 'in_progress', label: 'En curso' },
  { value: 'completed', label: 'Completadas' },
  { value: 'cancelled', label: 'Canceladas' },
  { value: 'no_show', label: 'No presentado' },
]

function SiteVisitDetailRoute() {
  const { visitId } = useParams<{ visitId: string }>()
  const { setActiveTab } = useSiteVisitStore()
  const { data: visit } = useSiteVisit(visitId ?? null)

  useEffect(() => {
    setActiveTab('info')
  }, [visitId])

  if (!visit) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gray-400">
        Cargando...
      </div>
    )
  }

  return <SiteVisitDetail visit={visit} />
}

export function SiteVisitsPage() {
  const [showForm, setShowForm] = useState(false)
  const {
    searchQuery,
    statusFilter,
    setSearchQuery,
    setStatusFilter,
  } = useSiteVisitStore()

  const { data, isLoading } = useSiteVisits({
    q: searchQuery || undefined,
    status: statusFilter ?? undefined,
    limit: 100,
  })

  const visits = data?.items ?? []
  const detailMatch = useMatch('/visitas/:visitId')
  const isDetailSelected = !!detailMatch

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          'flex flex-col border-r border-gray-100 min-w-0',
          isDetailSelected
            ? 'hidden lg:flex lg:w-[45%] lg:shrink-0'
            : 'flex flex-1',
        )}
      >
        {/* Header */}
        <div className="shrink-0 border-b border-gray-100 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin size={18} className="text-gray-600" />
              <h1 className="text-lg font-semibold text-gray-900">Visitas técnicas</h1>
              {data && (
                <span className="text-sm text-gray-400">({data.total})</span>
              )}
            </div>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus size={15} />
              <span className="hidden sm:inline">Nueva visita</span>
              <span className="sm:hidden">Nueva</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por cliente, dirección..."
              className="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status filter pills */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setStatusFilter(null)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                statusFilter === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Todas
            </button>
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() =>
                  setStatusFilter(opt.value === statusFilter ? null : opt.value)
                }
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                  statusFilter === opt.value
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          <SiteVisitList visits={visits} isLoading={isLoading} />
        </div>
      </div>

      {/* Right panel — detail via nested routes */}
      <div
        className={cn(
          'flex-1 flex flex-col overflow-hidden min-w-0',
          !isDetailSelected && 'hidden lg:flex',
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center text-sm text-gray-400">
                Selecciona una visita para ver el detalle
              </div>
            }
          />
          <Route path=":visitId" element={<SiteVisitDetailRoute />} />
        </Routes>
      </div>

      {showForm && <SiteVisitForm onClose={() => setShowForm(false)} />}
    </div>
  )
}
