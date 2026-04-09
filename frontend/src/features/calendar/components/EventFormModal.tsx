import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { X, Trash2 } from 'lucide-react'
import {
  useCreateCalendarEvent,
  useUpdateCalendarEvent,
  useDeleteCalendarEvent,
} from '../hooks/use-calendar'
import type { CalendarEventResponse } from '../types'

const PRESET_COLORS = [
  '#8b5cf6', '#3b82f6', '#10b981', '#f97316',
  '#ef4444', '#ec4899', '#f59e0b', '#6b7280',
]

const schema = z.object({
  title: z.string().min(1, 'El título es obligatorio').max(255),
  description: z.string().nullable().optional(),
  start_datetime: z.string().min(1, 'La fecha de inicio es obligatoria'),
  end_datetime: z.string().nullable().optional(),
  all_day: z.boolean(),
  color: z.string(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onClose: () => void
  initialDate?: string | null
  editEvent?: CalendarEventResponse | null
}

export function EventFormModal({ onClose, initialDate, editEvent }: Props) {
  const create = useCreateCalendarEvent()
  const update = useUpdateCalendarEvent()
  const remove = useDeleteCalendarEvent()

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: editEvent?.title ?? '',
      description: editEvent?.description ?? '',
      start_datetime: editEvent?.start_datetime ?? (initialDate ?? ''),
      end_datetime: editEvent?.end_datetime ?? '',
      all_day: editEvent?.all_day ?? true,
      color: editEvent?.color ?? '#8b5cf6',
    },
  })

  const allDay = watch('all_day')
  const selectedColor = watch('color')

  const onSubmit = async (values: FormValues) => {
    const payload = {
      title: values.title,
      description: values.description || null,
      start_datetime: values.start_datetime,
      end_datetime: values.end_datetime || null,
      all_day: values.all_day,
      color: values.color,
    }
    if (editEvent) {
      await update.mutateAsync({ id: editEvent.id, data: payload })
    } else {
      await create.mutateAsync(payload)
    }
    onClose()
  }

  const handleDelete = async () => {
    if (!editEvent) return
    if (!window.confirm('¿Eliminar este evento?')) return
    await remove.mutateAsync(editEvent.id)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">
            {editEvent ? 'Editar evento' : 'Nuevo evento'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
            <input
              {...register('title')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Nombre del evento"
            />
            {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title.message}</p>}
          </div>

          {/* All day toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="all_day"
              {...register('all_day')}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <label htmlFor="all_day" className="text-sm text-gray-700">Todo el día</label>
          </div>

          {/* Start */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {allDay ? 'Fecha' : 'Inicio'}
            </label>
            <input
              {...register('start_datetime')}
              type={allDay ? 'date' : 'datetime-local'}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            {errors.start_datetime && <p className="text-xs text-red-500 mt-1">{errors.start_datetime.message}</p>}
          </div>

          {/* End */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {allDay ? 'Fecha fin (opcional)' : 'Fin (opcional)'}
            </label>
            <input
              {...register('end_datetime')}
              type={allDay ? 'date' : 'datetime-local'}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción (opcional)</label>
            <textarea
              {...register('description')}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
              placeholder="Notas adicionales..."
            />
          </div>

          {/* Color picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
            <div className="flex gap-2 flex-wrap">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setValue('color', c)}
                  className="w-7 h-7 rounded-full border-2 transition-transform hover:scale-110"
                  style={{
                    backgroundColor: c,
                    borderColor: selectedColor === c ? '#111' : 'transparent',
                  }}
                />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            {editEvent ? (
              <button
                type="button"
                onClick={handleDelete}
                disabled={remove.isPending}
                className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
              >
                <Trash2 size={14} />
                Eliminar
              </button>
            ) : <div />}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSubmitting || create.isPending || update.isPending}
                className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50"
              >
                {editEvent ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
