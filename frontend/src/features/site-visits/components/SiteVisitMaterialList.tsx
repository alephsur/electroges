import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { SiteVisit } from '../types'
import { useAddMaterial, useDeleteMaterial } from '../hooks/use-site-visit-materials'
import { SiteVisitMaterialForm } from './SiteVisitMaterialForm'

interface SiteVisitMaterialListProps {
  visit: SiteVisit
}

export function SiteVisitMaterialList({ visit }: SiteVisitMaterialListProps) {
  const [showForm, setShowForm] = useState(false)
  const addMaterial = useAddMaterial(visit.id)
  const deleteMaterial = useDeleteMaterial(visit.id)

  const isEditable = visit.status === 'scheduled' || visit.status === 'in_progress'
  const materials = visit.materials

  const total = materials.reduce((sum, m) => sum + (m.subtotal ?? 0), 0)

  return (
    <div className="space-y-4">
      {materials.length === 0 && !showForm ? (
        <p className="text-sm text-gray-400 py-4 text-center">Sin materiales estimados</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="pb-2 pr-4">Material</th>
              <th className="pb-2 pr-4 text-right">Cant.</th>
              <th className="pb-2 pr-4">Ud.</th>
              <th className="pb-2 pr-4 text-right">€/ud</th>
              <th className="pb-2 text-right">Subtotal</th>
              {isEditable && <th className="pb-2 w-6" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {materials.map((m) => (
              <tr key={m.id}>
                <td className="py-2 pr-4">
                  <span className="font-medium text-gray-900">
                    {m.inventory_item_name ?? m.description ?? '—'}
                  </span>
                  {m.inventory_item_name && m.description && (
                    <span className="block text-xs text-gray-400">{m.description}</span>
                  )}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums">{m.estimated_qty}</td>
                <td className="py-2 pr-4 text-gray-500">{m.unit ?? '—'}</td>
                <td className="py-2 pr-4 text-right tabular-nums">
                  {m.unit_cost != null
                    ? m.unit_cost.toLocaleString('es-ES', { minimumFractionDigits: 2 })
                    : '—'}
                </td>
                <td className="py-2 text-right font-medium tabular-nums">
                  {m.subtotal != null
                    ? m.subtotal.toLocaleString('es-ES', { minimumFractionDigits: 2 }) + ' €'
                    : '—'}
                </td>
                {isEditable && (
                  <td className="py-2 pl-2">
                    <button
                      onClick={() => deleteMaterial.mutate(m.id)}
                      disabled={deleteMaterial.isPending}
                      className="text-gray-300 hover:text-red-500 disabled:opacity-50"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
          {total > 0 && (
            <tfoot>
              <tr className="border-t border-gray-200">
                <td
                  colSpan={isEditable ? 4 : 4}
                  className="pt-2 text-sm font-medium text-gray-700"
                >
                  Total estimado
                </td>
                <td className="pt-2 text-right font-semibold text-gray-900 tabular-nums">
                  {total.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €
                </td>
                {isEditable && <td />}
              </tr>
            </tfoot>
          )}
        </table>
      )}

      {showForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <SiteVisitMaterialForm
            onSubmit={(data) =>
              addMaterial.mutate(data, { onSuccess: () => setShowForm(false) })
            }
            onCancel={() => setShowForm(false)}
            isLoading={addMaterial.isPending}
          />
        </div>
      )}

      {isEditable && !showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700"
        >
          <Plus size={14} />
          Añadir material
        </button>
      )}
    </div>
  )
}
