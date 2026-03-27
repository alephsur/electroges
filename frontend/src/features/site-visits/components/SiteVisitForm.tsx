import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { X } from 'lucide-react'
import { useCustomers } from '@/features/customers/hooks/use-customers'
import { useCreateSiteVisit } from '../hooks/use-site-visits'
import type { SiteVisitCreatePayload } from '../types'

const schema = z
  .object({
    mode: z.enum(['customer', 'cold']),
    customer_id: z.string().optional().nullable(),
    contact_name: z.string().optional().nullable(),
    contact_phone: z.string().optional().nullable(),
    address_text: z.string().optional().nullable(),
    visit_date: z.string().min(1, 'La fecha es obligatoria'),
    estimated_duration_hours: z.coerce.number().nonnegative().optional().nullable(),
    description: z.string().optional().nullable(),
    work_scope: z.string().optional().nullable(),
    technical_notes: z.string().optional().nullable(),
    estimated_hours: z.coerce.number().nonnegative().optional().nullable(),
    estimated_budget: z.coerce.number().nonnegative().optional().nullable(),
  })
  .superRefine((data, ctx) => {
    if (data.mode === 'cold' && !data.contact_name) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'El nombre de contacto es obligatorio',
        path: ['contact_name'],
      })
    }
    if (data.mode === 'cold' && !data.address_text) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'La dirección es obligatoria',
        path: ['address_text'],
      })
    }
    if (data.mode === 'customer' && !data.address_text) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'La dirección es obligatoria',
        path: ['address_text'],
      })
    }
  })

type FormValues = z.infer<typeof schema>

interface SiteVisitFormProps {
  onClose: () => void
}

export function SiteVisitForm({ onClose }: SiteVisitFormProps) {
  const [customerSearch, setCustomerSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const { data: customersData } = useCustomers({
    q: customerSearch || undefined,
    limit: 10,
  })
  const createVisit = useCreateSiteVisit()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: 'customer',
      visit_date: new Date(new Date().setMinutes(0, 0, 0)).toISOString().slice(0, 16),
    },
  })

  const mode = watch('mode')
  const selectedCustomerId = watch('customer_id')

  const handleFormSubmit = (values: FormValues) => {
    const payload: SiteVisitCreatePayload = {
      customer_id: values.mode === 'customer' ? (values.customer_id ?? null) : null,
      address_text: values.address_text ?? null,
      contact_name: values.contact_name ?? null,
      contact_phone: values.contact_phone ?? null,
      visit_date: new Date(values.visit_date).toISOString(),
      estimated_duration_hours: values.estimated_duration_hours ?? null,
      description: values.description ?? null,
      work_scope: values.work_scope ?? null,
      technical_notes: values.technical_notes ?? null,
      estimated_hours: values.estimated_hours ?? null,
      estimated_budget: values.estimated_budget ?? null,
    }
    createVisit.mutate(payload, { onSuccess: onClose })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900">Nueva visita técnica</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6 p-6">
          {/* Section 1: Client and address */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-700">Cliente y dirección</h3>

            {/* Mode toggle */}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setValue('mode', 'customer')}
                className={`flex-1 rounded-md border py-2 text-sm font-medium transition-colors ${
                  mode === 'customer'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                Cliente existente
              </button>
              <button
                type="button"
                onClick={() => setValue('mode', 'cold')}
                className={`flex-1 rounded-md border py-2 text-sm font-medium transition-colors ${
                  mode === 'cold'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                Sin cliente (en frío)
              </button>
            </div>

            {mode === 'customer' ? (
              <div className="space-y-3">
                <div className="relative">
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Buscar cliente
                  </label>
                  <input
                    type="text"
                    value={customerSearch}
                    onChange={(e) => {
                      setCustomerSearch(e.target.value)
                      setValue('customer_id', null)
                      setShowDropdown(true)
                    }}
                    onFocus={() => setShowDropdown(true)}
                    placeholder="Nombre, NIF, email..."
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {showDropdown && !selectedCustomerId && customersData && customersData.items.length > 0 && (
                    <div className="absolute z-10 mt-1 max-h-40 w-full divide-y divide-gray-100 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-md">
                      {customersData.items.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onMouseDown={() => {
                            setValue('customer_id', c.id)
                            setCustomerSearch(c.name)
                            setShowDropdown(false)
                          }}
                          className="w-full px-3 py-2 text-left text-sm text-gray-900 hover:bg-gray-50"
                        >
                          <span className="font-medium">{c.name}</span>
                          {c.tax_id && (
                            <span className="ml-2 text-xs text-gray-400">{c.tax_id}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  {selectedCustomerId && (
                    <button
                      type="button"
                      onClick={() => {
                        setValue('customer_id', null)
                        setCustomerSearch('')
                      }}
                      className="mt-1 text-xs text-blue-600 hover:underline"
                    >
                      Cambiar cliente
                    </button>
                  )}
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dirección <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('address_text')}
                    type="text"
                    placeholder="Calle, número, piso, localidad..."
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.address_text && (
                    <p className="mt-1 text-xs text-red-600">{errors.address_text.message}</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Nombre de contacto <span className="text-red-500">*</span>
                    </label>
                    <input
                      {...register('contact_name')}
                      type="text"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {errors.contact_name && (
                      <p className="mt-1 text-xs text-red-600">{errors.contact_name.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Teléfono</label>
                    <input
                      {...register('contact_phone')}
                      type="tel"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dirección <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('address_text')}
                    type="text"
                    placeholder="Calle, número, localidad..."
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.address_text && (
                    <p className="mt-1 text-xs text-red-600">{errors.address_text.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Visit details */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-700">Detalles de la visita</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Fecha y hora <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('visit_date')}
                  type="datetime-local"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.visit_date && (
                  <p className="mt-1 text-xs text-red-600">{errors.visit_date.message}</p>
                )}
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Duración estimada (h)
                </label>
                <input
                  {...register('estimated_duration_hours')}
                  type="number"
                  step="0.5"
                  min="0"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Descripción (qué quiere el cliente)
              </label>
              <textarea
                {...register('description')}
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Notas técnicas{' '}
                <span className="text-xs font-normal text-amber-600">(solo interno)</span>
              </label>
              <textarea
                {...register('technical_notes')}
                rows={2}
                className="w-full rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Horas de trabajo estimadas
                </label>
                <input
                  {...register('estimated_hours')}
                  type="number"
                  step="0.5"
                  min="0"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Precio orientativo (€)
                </label>
                <input
                  {...register('estimated_budget')}
                  type="number"
                  step="0.01"
                  min="0"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createVisit.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createVisit.isPending ? 'Creando...' : 'Crear visita'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
