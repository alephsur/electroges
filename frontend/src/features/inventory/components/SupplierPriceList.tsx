import { useState } from 'react'
import { Star, Pencil, Trash2, Plus } from 'lucide-react'
import { useSetPreferredSupplier, useRemoveSupplier, useUpdateSupplierPrice } from '../hooks/use-supplier-items'
import { SupplierPriceForm } from './SupplierPriceForm'
import { getApiErrorMessage } from '@/shared/hooks/use-api-error'
import { cn } from '@/shared/utils/cn'
import type { InventoryItem, SupplierItem } from '../types'

interface SupplierPriceListProps {
  item: InventoryItem
}

function formatCurrency(value: number) {
  return value.toLocaleString('es-ES', { style: 'currency', currency: 'EUR', minimumFractionDigits: 4 })
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '—'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

interface EditRowState {
  supplierId: string
  unitCost: string
  supplierRef: string
  leadTimeDays: string
}

export function SupplierPriceList({ item }: SupplierPriceListProps) {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editState, setEditState] = useState<EditRowState>({
    supplierId: '',
    unitCost: '',
    supplierRef: '',
    leadTimeDays: '',
  })
  const [actionError, setActionError] = useState<string | null>(null)

  const setPreferred = useSetPreferredSupplier(item.id)
  const removeSupplier = useRemoveSupplier(item.id)
  const updatePrice = useUpdateSupplierPrice(item.id)

  const activeSuppliers = item.supplier_items.filter((s) => s.is_active)

  const cheapest =
    activeSuppliers.length >= 2
      ? activeSuppliers.reduce((a, b) => (Number(a.unit_cost) < Number(b.unit_cost) ? a : b))
      : null

  const preferred = item.preferred_supplier

  const handleSetPreferred = async (si: SupplierItem) => {
    if (si.is_preferred) return
    setActionError(null)
    try {
      await setPreferred.mutateAsync(si.id)
    } catch (err) {
      setActionError(getApiErrorMessage(err))
    }
  }

  const handleRemove = async (si: SupplierItem) => {
    if (!confirm(`¿Desvincular a ${si.supplier_name} de este material?`)) return
    setActionError(null)
    try {
      await removeSupplier.mutateAsync(si.id)
    } catch (err) {
      setActionError(getApiErrorMessage(err))
    }
  }

  const startEdit = (si: SupplierItem) => {
    setEditingId(si.id)
    setEditState({
      supplierId: si.supplier_id,
      unitCost: String(si.unit_cost),
      supplierRef: si.supplier_ref ?? '',
      leadTimeDays: si.lead_time_days ? String(si.lead_time_days) : '',
    })
  }

  const handleSaveEdit = async (si: SupplierItem) => {
    setActionError(null)
    try {
      await updatePrice.mutateAsync({
        supplierItemId: si.id,
        unit_cost: parseFloat(editState.unitCost),
        supplier_ref: editState.supplierRef || null,
        lead_time_days: editState.leadTimeDays ? parseInt(editState.leadTimeDays) : null,
      })
      setEditingId(null)
    } catch (err) {
      setActionError(getApiErrorMessage(err))
    }
  }

  if (activeSuppliers.length === 0) {
    return (
      <div>
        <div className="py-8 text-center text-sm text-gray-400">
          Este material no tiene proveedores vinculados
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700"
        >
          <Plus size={14} />
          Añadir proveedor
        </button>
        {showForm && <SupplierPriceForm itemId={item.id} onClose={() => setShowForm(false)} />}
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">
          {activeSuppliers.length} proveedor{activeSuppliers.length !== 1 ? 'es' : ''}
        </p>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700"
        >
          <Plus size={14} />
          Añadir proveedor
        </button>
      </div>

      {actionError && (
        <p className="mb-2 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{actionError}</p>
      )}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">
              <th className="px-4 py-3">Proveedor</th>
              <th className="px-4 py-3">Referencia</th>
              <th className="px-4 py-3 text-right">Precio actual</th>
              <th className="px-4 py-3 text-right">Último pagado</th>
              <th className="px-4 py-3">Último pedido</th>
              <th className="px-4 py-3">Plazo</th>
              <th className="px-4 py-3 text-center">Preferido</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {activeSuppliers.map((si) =>
              editingId === si.id ? (
                <tr key={si.id} className="bg-brand-50">
                  <td className="px-4 py-2 font-medium text-gray-800">{si.supplier_name}</td>
                  <td className="px-4 py-2">
                    <input
                      value={editState.supplierRef}
                      onChange={(e) => setEditState((s) => ({ ...s, supplierRef: e.target.value }))}
                      className="w-24 border border-gray-200 rounded px-2 py-1 text-xs"
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <input
                      type="number"
                      step="0.0001"
                      value={editState.unitCost}
                      onChange={(e) => setEditState((s) => ({ ...s, unitCost: e.target.value }))}
                      className="w-24 border border-gray-200 rounded px-2 py-1 text-xs text-right"
                    />
                  </td>
                  <td className="px-4 py-2 text-right text-gray-400 text-xs">
                    {si.last_purchase_cost ? formatCurrency(Number(si.last_purchase_cost)) : '—'}
                  </td>
                  <td className="px-4 py-2 text-gray-400 text-xs">{formatDate(si.last_purchase_date)}</td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min="1"
                      value={editState.leadTimeDays}
                      onChange={(e) =>
                        setEditState((s) => ({ ...s, leadTimeDays: e.target.value }))
                      }
                      placeholder="días"
                      className="w-16 border border-gray-200 rounded px-2 py-1 text-xs"
                    />
                  </td>
                  <td className="px-4 py-2 text-center">—</td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleSaveEdit(si)}
                        className="px-2 py-1 text-xs bg-brand-600 text-white rounded hover:bg-brand-700"
                      >
                        Guardar
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-2 py-1 text-xs text-gray-600 border border-gray-200 rounded hover:bg-gray-50"
                      >
                        Cancelar
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={si.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{si.supplier_name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                    {si.supplier_ref ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-800">
                    {formatCurrency(Number(si.unit_cost))}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {si.last_purchase_cost ? (
                      <span
                        className={cn(
                          'text-xs',
                          Number(si.last_purchase_cost) !== Number(si.unit_cost)
                            ? 'text-gray-400'
                            : 'text-gray-600',
                        )}
                      >
                        {formatCurrency(Number(si.last_purchase_cost))}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {formatDate(si.last_purchase_date)}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {si.lead_time_days ? `${si.lead_time_days} días` : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSetPreferred(si)}
                      title={si.is_preferred ? 'Proveedor preferido' : 'Marcar como preferido'}
                      className="transition-colors"
                    >
                      <Star
                        size={16}
                        className={
                          si.is_preferred
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-gray-300 hover:text-amber-300'
                        }
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => startEdit(si)}
                        className="p-1 text-gray-400 hover:text-brand-600"
                        title="Editar precio"
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                        onClick={() => handleRemove(si)}
                        className="p-1 text-gray-400 hover:text-red-600"
                        title="Desvincular proveedor"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      {cheapest && preferred && cheapest.id !== preferred.id && (
        <div className="mt-3 px-4 py-2.5 bg-green-50 border border-green-100 rounded-lg text-sm text-green-800">
          El proveedor más barato es{' '}
          <strong>{cheapest.supplier_name}</strong> con{' '}
          {formatCurrency(Number(cheapest.unit_cost))} / {item.unit}
          {Number(preferred.unit_cost) > 0 && (
            <>
              {' '}(
              {(
                ((Number(preferred.unit_cost) - Number(cheapest.unit_cost)) /
                  Number(preferred.unit_cost)) *
                100
              ).toFixed(1)}
              % más barato que el preferido)
            </>
          )}
        </div>
      )}

      {showForm && <SupplierPriceForm itemId={item.id} onClose={() => setShowForm(false)} />}
    </div>
  )
}
