import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X } from "lucide-react";
import { useCreateSupplierInventoryItem } from "../hooks/use-supplier-inventory";
import { getApiErrorMessage } from "@/shared/hooks/use-api-error";
import { cn } from "@/shared/utils/cn";

// ------------------------------------------------------------------ validation

const schema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  description: z.string().optional(),
  unit: z.string().min(1, "La unidad es obligatoria"),
  unit_cost: z.coerce.number().min(0, "El coste debe ser >= 0"),
  unit_price: z.coerce.number().min(0, "El precio debe ser >= 0"),
  stock_current: z.coerce.number().min(0, "El stock debe ser >= 0"),
  stock_min: z.coerce.number().min(0, "El stock mínimo debe ser >= 0"),
});

type FormValues = z.infer<typeof schema>;

const UNIT_OPTIONS = [
  { value: "ud", label: "Unidad (ud)" },
  { value: "m", label: "Metro (m)" },
  { value: "m2", label: "Metro cuadrado (m²)" },
  { value: "kg", label: "Kilogramo (kg)" },
  { value: "l", label: "Litro (l)" },
];

// ------------------------------------------------------------------ component

interface InventoryItemFormProps {
  supplierId: string;
  onClose: () => void;
}

export function InventoryItemForm({ supplierId, onClose }: InventoryItemFormProps) {
  const createMutation = useCreateSupplierInventoryItem(supplierId);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { unit: "ud", unit_cost: 0, unit_price: 0, stock_current: 0, stock_min: 0 },
  });

  const onSubmit = async (values: FormValues) => {
    await createMutation.mutateAsync(
      {
        ...values,
        description: values.description || null,
      },
      { onSuccess: onClose }
    );
  };

  const error = createMutation.error ? getApiErrorMessage(createMutation.error) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Nuevo artículo de inventario</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
        >
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <Field label="Nombre *" error={errors.name?.message}>
            <input {...register("name")} placeholder="Nombre del artículo" />
          </Field>

          <Field label="Descripción" error={errors.description?.message}>
            <input {...register("description")} placeholder="Descripción opcional" />
          </Field>

          <Field label="Unidad *" error={errors.unit?.message}>
            <select {...register("unit")}>
              {UNIT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Coste unitario (€)" error={errors.unit_cost?.message}>
              <input {...register("unit_cost")} type="number" step="0.0001" min="0" />
            </Field>
            <Field label="Precio de venta (€)" error={errors.unit_price?.message}>
              <input {...register("unit_price")} type="number" step="0.0001" min="0" />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Stock actual" error={errors.stock_current?.message}>
              <input {...register("stock_current")} type="number" step="0.001" min="0" />
            </Field>
            <Field label="Stock mínimo" error={errors.stock_min?.message}>
              <input {...register("stock_min")} type="number" step="0.001" min="0" />
            </Field>
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
            {createMutation.isPending ? "Guardando..." : "Crear artículo"}
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
