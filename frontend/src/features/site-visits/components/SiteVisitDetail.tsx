import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Clock, FileText, Image, MapPin, Package, User } from 'lucide-react'
import type { SiteVisit } from '../types'
import { useSiteVisitStore } from '../store/site-visit-store'
import { useUpdateSiteVisit, useUpdateSiteVisitStatus } from '../hooks/use-site-visits'
import { SiteVisitStatusBadge } from './SiteVisitStatusBadge'
import { SiteVisitMaterialList } from './SiteVisitMaterialList'
import { SiteVisitPhotoGallery } from './SiteVisitPhotoGallery'
import { SiteVisitDocumentList } from './SiteVisitDocumentList'
import { LinkCustomerModal } from './LinkCustomerModal'
import { BudgetFromVisitForm } from '@/features/budgets/components/BudgetFromVisitForm'

const infoSchema = z.object({
  description: z.string().optional().nullable(),
  work_scope: z.string().optional().nullable(),
  technical_notes: z.string().optional().nullable(),
  estimated_hours: z.coerce.number().nonnegative().optional().nullable(),
  estimated_budget: z.coerce.number().nonnegative().optional().nullable(),
  estimated_duration_hours: z.coerce.number().nonnegative().optional().nullable(),
})

type InfoFormValues = z.infer<typeof infoSchema>

interface SiteVisitDetailProps {
  visit: SiteVisit
}

export function SiteVisitDetail({ visit }: SiteVisitDetailProps) {
  const { activeTab, setActiveTab } = useSiteVisitStore()
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [showBudgetForm, setShowBudgetForm] = useState(false)
  const updateVisit = useUpdateSiteVisit()
  const updateStatus = useUpdateSiteVisitStatus()

  const isEditable = visit.status === 'scheduled' || visit.status === 'in_progress'

  const { register, handleSubmit, formState: { isDirty } } = useForm<InfoFormValues>({
    resolver: zodResolver(infoSchema),
    defaultValues: {
      description: visit.description,
      work_scope: visit.work_scope,
      technical_notes: visit.technical_notes,
      estimated_hours: visit.estimated_hours,
      estimated_budget: visit.estimated_budget,
      estimated_duration_hours: visit.estimated_duration_hours,
    },
  })

  const handleInfoSave = (values: InfoFormValues) => {
    updateVisit.mutate({ id: visit.id, ...values })
  }

  const handleStatusChange = (newStatus: string) => {
    updateStatus.mutate({ id: visit.id, status: newStatus })
  }

  const TABS = [
    { id: 'info' as const, label: 'Información', icon: <FileText size={13} /> },
    {
      id: 'materiales' as const,
      label: `Materiales (${visit.materials_count})`,
      icon: <Package size={13} />,
    },
    {
      id: 'fotos' as const,
      label: `Fotos (${visit.photos.length})`,
      icon: <Image size={13} />,
    },
    {
      id: 'documentos' as const,
      label: `Docs (${visit.documents.length})`,
      icon: <FileText size={13} />,
    },
  ]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 border-b border-gray-100 p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {visit.customer_id ? (
              <div className="flex items-center gap-2 flex-wrap">
                <User size={13} className="shrink-0 text-gray-400" />
                <span className="text-sm font-semibold text-gray-900">{visit.customer_name}</span>
                {visit.budgets_count > 0 && (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                    {visit.budgets_count} presupuesto{visit.budgets_count !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 flex-wrap">
                <User size={13} className="shrink-0 text-gray-300" />
                <span className="text-sm text-gray-400">Sin cliente registrado</span>
                <button
                  onClick={() => setShowLinkModal(true)}
                  className="text-xs font-medium text-blue-600 hover:underline"
                >
                  Vincular cliente
                </button>
              </div>
            )}
            <div className="mt-1 flex items-center gap-1.5 text-xs text-gray-500">
              <MapPin size={11} className="shrink-0" />
              <span className="truncate">{visit.address_display}</span>
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-xs text-gray-500">
              <Clock size={11} className="shrink-0" />
              <span>
                {new Date(visit.visit_date).toLocaleDateString('es-ES', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>
          <SiteVisitStatusBadge status={visit.status} />
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {visit.status === 'scheduled' && (
            <>
              <button
                onClick={() => handleStatusChange('in_progress')}
                disabled={updateStatus.isPending}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Iniciar visita
              </button>
              <button
                onClick={() => handleStatusChange('no_show')}
                disabled={updateStatus.isPending}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
              >
                No presentado
              </button>
              <button
                onClick={() => handleStatusChange('cancelled')}
                disabled={updateStatus.isPending}
                className="rounded-md border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
              >
                Cancelar
              </button>
            </>
          )}
          {visit.status === 'in_progress' && (
            <>
              <button
                onClick={() => handleStatusChange('completed')}
                disabled={updateStatus.isPending}
                className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                Completar visita
              </button>
              <button
                onClick={() => handleStatusChange('cancelled')}
                disabled={updateStatus.isPending}
                className="rounded-md border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
              >
                Cancelar
              </button>
            </>
          )}
          {visit.status === 'completed' && (
            <button
              onClick={() => setShowBudgetForm(true)}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
            >
              Crear presupuesto
            </button>
          )}
          {visit.status === 'no_show' && (
            <button
              onClick={() => handleStatusChange('scheduled')}
              disabled={updateStatus.isPending}
              className="rounded-md border border-blue-200 px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50"
            >
              Reprogramar
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="shrink-0 border-b border-gray-100 px-4">
        <div className="-mb-px flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'info' && (
          <form onSubmit={handleSubmit(handleInfoSave)} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Descripción del trabajo
              </label>
              <textarea
                {...register('description')}
                rows={3}
                disabled={!isEditable}
                placeholder="Qué quiere el cliente..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Alcance del trabajo
              </label>
              <textarea
                {...register('work_scope')}
                rows={3}
                disabled={!isEditable}
                placeholder="Tareas y alcance..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Notas técnicas{' '}
                <span className="text-xs font-normal text-amber-600">(solo interno)</span>
              </label>
              <textarea
                {...register('technical_notes')}
                rows={3}
                disabled={!isEditable}
                placeholder="Notas internas del técnico..."
                className="w-full rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-75"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Horas estimadas
                </label>
                <input
                  {...register('estimated_hours')}
                  type="number"
                  step="0.5"
                  min="0"
                  disabled={!isEditable}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Precio orient. (€)
                </label>
                <input
                  {...register('estimated_budget')}
                  type="number"
                  step="0.01"
                  min="0"
                  disabled={!isEditable}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Duración visita (h)
                </label>
                <input
                  {...register('estimated_duration_hours')}
                  type="number"
                  step="0.5"
                  min="0"
                  disabled={!isEditable}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                />
              </div>
            </div>
            {isEditable && (
              <button
                type="submit"
                disabled={!isDirty || updateVisit.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {updateVisit.isPending ? 'Guardando...' : 'Guardar cambios'}
              </button>
            )}
          </form>
        )}
        {activeTab === 'materiales' && <SiteVisitMaterialList visit={visit} />}
        {activeTab === 'fotos' && <SiteVisitPhotoGallery visit={visit} />}
        {activeTab === 'documentos' && <SiteVisitDocumentList visit={visit} />}
      </div>

      {showLinkModal && (
        <LinkCustomerModal visit={visit} onClose={() => setShowLinkModal(false)} />
      )}
      {showBudgetForm && (
        <BudgetFromVisitForm
          initialVisitId={visit.id}
          onClose={() => setShowBudgetForm(false)}
        />
      )}
    </div>
  )
}
