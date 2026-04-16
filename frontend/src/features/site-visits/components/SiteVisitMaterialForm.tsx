import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { InventoryItemPicker } from '@/shared/components/InventoryItemPicker'
import type { InventoryItem } from '@/features/inventory/types'
import type { SiteVisitMaterialCreatePayload } from '../types'

const schema = z
  .object({
    inventory_item_id: z.string().optional().nullable(),
    description: z.string().optional().nullable(),
    estimated_qty: z.coerce.number().positive('La cantidad debe ser mayor a 0'),
    unit: z.string().optional().nullable(),
    unit_cost: z.coerce.number().nonnegative().optional().nullable(),
  })
  .refine((d) => !!d.inventory_item_id || !!d.description, {
    message: 'Selecciona un material del inventario o escribe una descripción',
    path: ['description'],
  })

type FormValues = z.infer<typeof schema>

interface SiteVisitMaterialFormProps {
  onSubmit: (data: SiteVisitMaterialCreatePayload) => void
  onCancel: () => void
  isLoading?: boolean
}

export function SiteVisitMaterialForm({
  onSubmit,
  onCancel,
  isLoading,
}: SiteVisitMaterialFormProps) {
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const inventoryItemId = watch('inventory_item_id')

  const handleItemChange = (item: InventoryItem | null) => {
    setSelectedItem(item)
    setValue('inventory_item_id', item?.id ?? null)
    if (item) {
      setValue('description', item.name)
      setValue('unit', item.unit)
      setValue('unit_cost', Number(item.unit_cost_avg ?? item.unit_cost ?? 0) || null)
    }
  }

  const handleFormSubmit = (values: FormValues) => {
    onSubmit({
      inventory_item_id: values.inventory_item_id || null,
      description: values.description || null,
      estimated_qty: values.estimated_qty,
      unit: values.unit || null,
      unit_cost: values.unit_cost ?? null,
    })
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {/* Inventory picker */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Material del inventario
        </label>
        <InventoryItemPicker
          value={selectedItem}
          onChange={handleItemChange}
          placeholder="Buscar en inventario (opcional)…"
        />
      </div>

      {/* Description */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Descripción del material{' '}
          {!inventoryItemId && <span className="text-red-500">*</span>}
        </label>
        <input
          {...register('description')}
          type="text"
          placeholder="Ej: Cable H07V-K 1.5mm²"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.description && (
          <p className="mt-1 text-xs text-red-600">{errors.description.message}</p>
        )}
      </div>

      {/* Qty / Unit / Price */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Cantidad <span className="text-red-500">*</span>
          </label>
          <input
            {...register('estimated_qty')}
            type="number"
            step="0.001"
            min="0"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.estimated_qty && (
            <p className="mt-1 text-xs text-red-600">{errors.estimated_qty.message}</p>
          )}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Unidad</label>
          <input
            {...register('unit')}
            type="text"
            placeholder="m, ud, kg…"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Precio unit. (€)</label>
          <input
            {...register('unit_cost')}
            type="number"
            step="0.0001"
            min="0"
            placeholder="0.00"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? 'Guardando…' : 'Añadir material'}
        </button>
      </div>
    </form>
  )
}
