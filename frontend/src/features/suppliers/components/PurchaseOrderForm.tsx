import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2, X } from "lucide-react";
import { useCreatePurchaseOrder } from "../hooks/use-purchase-orders";
import { useInventoryItems } from "@/features/inventory/hooks/use-inventory-items";
import { getApiErrorMessage } from "@/shared/hooks/use-api-error";
import { cn } from "@/shared/utils/cn";

// ------------------------------------------------------------------ validation

const lineSchema = z
  .object({
    inventory_item_id: z.string().optional(),
    description: z.string().optional(),
    quantity: z.coerce.number().gt(0, "La cantidad debe ser > 0"),
    unit_cost: z.coerce.number().min(0, "El coste debe ser >= 0"),
  })
  .refine(
    (v) => v.inventory_item_id || (v.description && v.description.trim().length > 0),
    { message: "Selecciona un artículo o escribe una descripción", path: ["description"] }
  );

const schema = z.object({
  order_date: z.string().min(1, "La fecha es obligatoria"),
  expected_date: z.string().optional(),
  notes: z.string().optional(),
  lines: z.array(lineSchema).min(1, "El pedido debe tener al menos una línea"),
});

type FormValues = z.infer<typeof schema>;

// ------------------------------------------------------------------ component

interface PurchaseOrderFormProps {
  supplierId: string;
  onClose: () => void;
}

export function PurchaseOrderForm({ supplierId, onClose }: PurchaseOrderFormProps) {
  const createMutation = useCreatePurchaseOrder(supplierId);
  const { data: itemsData } = useInventoryItems({ supplier_id: supplierId, limit: 200 });
  const items = itemsData?.items ?? [];

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      order_date: new Date().toISOString().slice(0, 10),
      lines: [{ inventory_item_id: "", description: "", quantity: 1, unit_cost: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  const watchedLines = watch("lines");

  const lineTotal = (idx: number) => {
    const line = watchedLines[idx];
    if (!line) return "0.00";
    return (Number(line.quantity) * Number(line.unit_cost)).toFixed(2);
  };

  const orderTotal = watchedLines.reduce(
    (acc, l) => acc + Number(l.quantity) * Number(l.unit_cost),
    0
  );

  const onSubmit = async (values: FormValues) => {
    await createMutation.mutateAsync(
      {
        supplier_id: supplierId,
        order_date: values.order_date,
        expected_date: values.expected_date || null,
        notes: values.notes || null,
        lines: values.lines.map((l) => ({
          inventory_item_id: l.inventory_item_id || null,
          description: l.description || null,
          quantity: l.quantity,
          unit_cost: l.unit_cost,
        })),
      },
      { onSuccess: onClose }
    );
  };

  const error = createMutation.error ? getApiErrorMessage(createMutation.error) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Nuevo pedido de compra</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex-1 overflow-y-auto px-6 py-4 space-y-5"
        >
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Header fields */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Fecha del pedido *" error={errors.order_date?.message}>
              <input {...register("order_date")} type="date" />
            </Field>
            <Field label="Fecha esperada de entrega" error={errors.expected_date?.message}>
              <input {...register("expected_date")} type="date" />
            </Field>
          </div>

          <Field label="Notas" error={errors.notes?.message}>
            <textarea {...register("notes")} rows={2} className="resize-none" placeholder="Observaciones internas..." />
          </Field>

          {/* Lines */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700">Líneas del pedido</h3>
              <button
                type="button"
                onClick={() =>
                  append({ inventory_item_id: "", description: "", quantity: 1, unit_cost: 0 })
                }
                className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                <Plus size={13} />
                Añadir línea
              </button>
            </div>

            {(errors.lines as { message?: string } | undefined)?.message && (
              <p className="mb-2 text-xs text-red-500">{(errors.lines as { message?: string }).message}</p>
            )}

            <div className="space-y-3">
              {fields.map((field, idx) => {
                const lineErrors = errors.lines?.[idx];
                return (
                  <div
                    key={field.id}
                    className="grid grid-cols-12 gap-2 items-start p-3 bg-gray-50 rounded-lg"
                  >
                    {/* Item selector */}
                    <div className="col-span-4">
                      <label className="block text-xs text-gray-500 mb-1">Artículo</label>
                      <select
                        {...register(`lines.${idx}.inventory_item_id`)}
                        className={cn(
                          "w-full border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                          lineErrors?.inventory_item_id ? "border-red-400" : "border-gray-300"
                        )}
                      >
                        <option value="">Sin artículo (texto libre)</option>
                        {items.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name} ({item.unit})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Description */}
                    <div className="col-span-3">
                      <label className="block text-xs text-gray-500 mb-1">Descripción</label>
                      <input
                        {...register(`lines.${idx}.description`)}
                        placeholder="Descripción..."
                        className={cn(
                          "w-full border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                          lineErrors?.description ? "border-red-400" : "border-gray-300"
                        )}
                      />
                      {lineErrors?.description && (
                        <p className="mt-0.5 text-xs text-red-500">{lineErrors.description.message}</p>
                      )}
                    </div>

                    {/* Quantity */}
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-1">Cantidad</label>
                      <input
                        {...register(`lines.${idx}.quantity`)}
                        type="number"
                        step="0.001"
                        min="0.001"
                        className={cn(
                          "w-full border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                          lineErrors?.quantity ? "border-red-400" : "border-gray-300"
                        )}
                      />
                    </div>

                    {/* Unit cost */}
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-1">Coste (€)</label>
                      <input
                        {...register(`lines.${idx}.unit_cost`)}
                        type="number"
                        step="0.0001"
                        min="0"
                        className={cn(
                          "w-full border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                          lineErrors?.unit_cost ? "border-red-400" : "border-gray-300"
                        )}
                      />
                    </div>

                    {/* Subtotal + remove */}
                    <div className="col-span-1 flex flex-col items-end gap-1 pt-5">
                      <span className="text-sm font-medium text-gray-700">
                        {lineTotal(idx)} €
                      </span>
                      {fields.length > 1 && (
                        <button
                          type="button"
                          onClick={() => remove(idx)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Order total */}
            <div className="flex justify-end mt-3 pr-1">
              <span className="text-sm font-semibold text-gray-900">
                Total: {orderTotal.toFixed(2)} €
              </span>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            disabled={createMutation.isPending}
            onClick={handleSubmit(onSubmit)}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {createMutation.isPending ? "Guardando..." : "Crear pedido"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ helpers

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactElement;
}) {
  const base =
    "w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500";
  const border = error ? "border-red-400" : "border-gray-300";
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {{
        ...children,
        props: { ...children.props, className: cn(base, border, children.props.className) },
      }}
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}
