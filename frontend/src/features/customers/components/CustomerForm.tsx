import { useState } from 'react'
import type { CustomerCreatePayload, CustomerType, CustomerUpdatePayload } from '../types'

interface CustomerFormProps {
  initial?: Partial<CustomerCreatePayload & CustomerUpdatePayload>
  onSubmit: (data: CustomerCreatePayload) => void
  onCancel: () => void
  isLoading?: boolean
}

const TYPE_LABELS: Record<CustomerType, { name: string; taxId: string; contact?: string }> = {
  individual: { name: 'Nombre y apellidos', taxId: 'NIF' },
  company: { name: 'Razón social', taxId: 'CIF', contact: 'Persona de contacto' },
  community: { name: 'Nombre de la comunidad', taxId: 'CIF', contact: 'Administrador / contacto' },
}

export function CustomerForm({ initial, onSubmit, onCancel, isLoading }: CustomerFormProps) {
  const [form, setForm] = useState<CustomerCreatePayload>({
    customer_type: initial?.customer_type ?? 'individual',
    name: initial?.name ?? '',
    tax_id: initial?.tax_id ?? '',
    email: initial?.email ?? '',
    phone: initial?.phone ?? '',
    phone_secondary: initial?.phone_secondary ?? '',
    contact_person: initial?.contact_person ?? '',
    notes: initial?.notes ?? '',
    initial_address: null,
  })
  const [addAddress, setAddAddress] = useState(false)
  const [addrForm, setAddrForm] = useState({
    address_type: 'service' as 'fiscal' | 'service',
    label: '',
    street: '',
    city: '',
    postal_code: '',
    province: '',
  })

  const set = (field: keyof CustomerCreatePayload, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const labels = TYPE_LABELS[form.customer_type]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...form,
      tax_id: form.tax_id || null,
      email: form.email || null,
      phone: form.phone || null,
      phone_secondary: form.phone_secondary || null,
      contact_person: form.contact_person || null,
      notes: form.notes || null,
      initial_address: addAddress
        ? {
            address_type: addrForm.address_type,
            label: addrForm.label || null,
            street: addrForm.street,
            city: addrForm.city,
            postal_code: addrForm.postal_code,
            province: addrForm.province || null,
            is_default: true,
          }
        : null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Customer type */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Tipo de cliente</label>
        <div className="flex gap-2">
          {(['individual', 'company', 'community'] as CustomerType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => set('customer_type', type)}
              className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                form.customer_type === type
                  ? 'border-brand-500 bg-brand-50 text-brand-700 font-medium'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {type === 'individual' ? 'Particular' : type === 'company' ? 'Empresa' : 'Comunidad'}
            </button>
          ))}
        </div>
      </div>

      {/* Name */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          {labels.name} <span className="text-red-500">*</span>
        </label>
        <input
          required
          type="text"
          value={form.name}
          onChange={(e) => set('name', e.target.value)}
          minLength={2}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Tax ID */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{labels.taxId}</label>
          <input
            type="text"
            value={form.tax_id ?? ''}
            onChange={(e) => set('tax_id', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Email */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
          <input
            type="email"
            value={form.email ?? ''}
            onChange={(e) => set('email', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Phone */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Teléfono</label>
          <input
            type="tel"
            value={form.phone ?? ''}
            onChange={(e) => set('phone', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Secondary phone */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Teléfono secundario</label>
          <input
            type="tel"
            value={form.phone_secondary ?? ''}
            onChange={(e) => set('phone_secondary', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Contact person (company / community only) */}
      {labels.contact && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{labels.contact}</label>
          <input
            type="text"
            value={form.contact_person ?? ''}
            onChange={(e) => set('contact_person', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      )}

      {/* Notes */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Notas</label>
        <textarea
          value={form.notes ?? ''}
          onChange={(e) => set('notes', e.target.value)}
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
        />
      </div>

      {/* Initial address toggle */}
      {!initial && (
        <>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={addAddress}
              onChange={(e) => setAddAddress(e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-600">Añadir dirección ahora</span>
          </label>

          {addAddress && (
            <div className="border border-gray-200 rounded-lg p-3 space-y-3 bg-gray-50">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Dirección inicial
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                  <select
                    value={addrForm.address_type}
                    onChange={(e) =>
                      setAddrForm((p) => ({
                        ...p,
                        address_type: e.target.value as 'fiscal' | 'service',
                      }))
                    }
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                  >
                    <option value="service">Servicio</option>
                    <option value="fiscal">Fiscal</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Etiqueta</label>
                  <input
                    type="text"
                    value={addrForm.label}
                    onChange={(e) => setAddrForm((p) => ({ ...p, label: e.target.value }))}
                    placeholder="Casa, Oficina..."
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Calle <span className="text-red-500">*</span>
                </label>
                <input
                  required={addAddress}
                  type="text"
                  value={addrForm.street}
                  onChange={(e) => setAddrForm((p) => ({ ...p, street: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Ciudad <span className="text-red-500">*</span>
                  </label>
                  <input
                    required={addAddress}
                    type="text"
                    value={addrForm.city}
                    onChange={(e) => setAddrForm((p) => ({ ...p, city: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Código postal <span className="text-red-500">*</span>
                  </label>
                  <input
                    required={addAddress}
                    type="text"
                    value={addrForm.postal_code}
                    onChange={(e) => setAddrForm((p) => ({ ...p, postal_code: e.target.value }))}
                    maxLength={10}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Provincia</label>
                <input
                  type="text"
                  value={addrForm.province}
                  onChange={(e) => setAddrForm((p) => ({ ...p, province: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                />
              </div>
            </div>
          )}
        </>
      )}

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
          {isLoading ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear cliente'}
        </button>
      </div>
    </form>
  )
}
