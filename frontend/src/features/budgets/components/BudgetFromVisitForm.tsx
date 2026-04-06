import { useState } from 'react'
import { X, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { SiteVisitListResponse } from '@/features/site-visits/types'
import { useCreateBudgetFromVisit } from '../hooks/use-budgets'

interface BudgetFromVisitFormProps {
  initialVisitId?: string
  onClose: () => void
}

export function BudgetFromVisitForm({ initialVisitId, onClose }: BudgetFromVisitFormProps) {
  const createFromVisit = useCreateBudgetFromVisit()
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2>(initialVisitId ? 2 : 1)
  const [selectedVisitId, setSelectedVisitId] = useState(initialVisitId ?? '')
  const [notes, setNotes] = useState('')
  const [clientNotes, setClientNotes] = useState('')
  const [discount, setDiscount] = useState('0')

  const { data: visitsData, isLoading: visitsLoading } = useQuery({
    queryKey: ['site-visits', 'completed'],
    queryFn: async () => {
      const { data } = await apiClient.get<SiteVisitListResponse>('/api/v1/site-visits', {
        params: { status: 'completed', limit: 100 },
      })
      return data
    },
    enabled: step === 1,
  })

  const completedVisits = visitsData?.items ?? []

  const handleCreate = () => {
    createFromVisit.mutate(
      {
        site_visit_id: selectedVisitId,
        discount_pct: parseFloat(discount) || 0,
        notes: notes || null,
        client_notes: clientNotes || null,
      },
      {
        onSuccess: (data) => {
          navigate(`/presupuestos/${data.id}`)
          onClose()
        },
      },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              Presupuesto desde visita técnica
            </h2>
            <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
              <span className={step >= 1 ? 'text-blue-600 font-medium' : ''}>
                1. Seleccionar visita
              </span>
              <ChevronRight size={12} />
              <span className={step === 2 ? 'text-blue-600 font-medium' : ''}>
                2. Revisar y confirmar
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        {/* Step 1: select visit */}
        {step === 1 && (
          <div className="px-6 py-4">
            {visitsLoading ? (
              <div className="py-6 text-center text-sm text-gray-400">
                Cargando visitas completadas...
              </div>
            ) : completedVisits.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400">
                No hay visitas técnicas completadas sin presupuesto.
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {completedVisits.map((v) => (
                  <div
                    key={v.id}
                    onClick={() => setSelectedVisitId(v.id)}
                    className={`cursor-pointer rounded-md border px-4 py-3 transition-colors hover:bg-gray-50 ${
                      selectedVisitId === v.id
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-800">
                          {v.customer_name ?? v.contact_name ?? 'Sin cliente'}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {v.address_display} ·{' '}
                          {new Date(v.visit_date).toLocaleDateString('es-ES')}
                        </div>
                      </div>
                      {v.materials_count > 0 && (
                        <span className="text-xs text-gray-400">
                          {v.materials_count} materiales
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!selectedVisitId}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}

        {/* Step 2: review and confirm */}
        {step === 2 && (
          <div className="px-6 py-4 space-y-4">
            <div className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
              Las líneas se generarán automáticamente desde los materiales de la visita.
              Podrás editarlas una vez creado el presupuesto.
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Descuento global (%)
                </label>
                <input
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Notas para el cliente
              </label>
              <textarea
                value={clientNotes}
                onChange={(e) => setClientNotes(e.target.value)}
                rows={2}
                placeholder="Texto visible en el PDF..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-700">
                Notas internas
                <span className="text-xs font-normal text-amber-600">(solo interno)</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Notas no visibles en el PDF..."
                className="w-full rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setStep(1)}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Atrás
              </button>
              <button
                onClick={handleCreate}
                disabled={createFromVisit.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createFromVisit.isPending ? 'Creando...' : 'Crear presupuesto'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
