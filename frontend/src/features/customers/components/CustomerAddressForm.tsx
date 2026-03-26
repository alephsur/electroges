import { useState } from 'react'
import type { CustomerAddress, CustomerAddressCreatePayload } from '../types'

interface CustomerAddressFormProps {
  initial?: CustomerAddress
  onSubmit: (data: CustomerAddressCreatePayload) => void
  onCancel: () => void
  isLoading?: boolean
}

export function CustomerAddressForm({
  initial,
  onSubmit,
  onCancel,
  isLoading,
}: CustomerAddressFormProps) {
  const [form, setForm] = useState<CustomerAddressCreatePayload>({
    address_type: initial?.address_type ?? 'service',
    label: initial?.label ?? '',
    street: initial?.street ?? '',
    city: initial?.city ?? '',
    postal_code: initial?.postal_code ?? '',
    province: initial?.province ?? '',
    is_default: initial?.is_default ?? false,
  })

  const set = (field: keyof typeof form, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...form,
      label: form.label || null,
      province: form.province || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {/* Type */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
          <select
            value={form.address_type}
            onChange={(e) => set('address_type', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="service">Servicio</option>
            <option value="fiscal">Fiscal</option>
          </select>
        </div>

        {/* Label */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Etiqueta</label>
          <input
            type="text"
            value={form.label ?? ''}
            onChange={(e) => set('label', e.target.value)}
            placeholder="Casa, Oficina, Portal A..."
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Street */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Calle <span className="text-red-500">*</span>
        </label>
        <input
          required
          type="text"
          value={form.street}
          onChange={(e) => set('street', e.target.value)}
          placeholder="Calle Mayor, 1, 2ª B"
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* City */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Ciudad <span className="text-red-500">*</span>
          </label>
          <input
            required
            type="text"
            value={form.city}
            onChange={(e) => set('city', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Postal code */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Código postal <span className="text-red-500">*</span>
          </label>
          <input
            required
            type="text"
            value={form.postal_code}
            onChange={(e) => set('postal_code', e.target.value)}
            maxLength={10}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Province */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Provincia</label>
        <input
          type="text"
          value={form.province ?? ''}
          onChange={(e) => set('province', e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {/* Default */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={form.is_default}
          onChange={(e) => set('is_default', e.target.checked)}
          className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
        />
        <span className="text-sm text-gray-600">Marcar como dirección predeterminada</span>
      </label>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? 'Guardando...' : 'Guardar dirección'}
        </button>
      </div>
    </form>
  )
}
