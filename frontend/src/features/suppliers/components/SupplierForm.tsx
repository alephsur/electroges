import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X } from "lucide-react";
import { useCreateSupplier, useUpdateSupplier } from "../hooks/use-suppliers";
import { getApiErrorMessage } from "@/shared/hooks/use-api-error";
import { cn } from "@/shared/utils/cn";
import type { Supplier } from "../types";

// ------------------------------------------------------------------ validation

const schema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  tax_id: z.string().optional(),
  email: z.preprocess(
    (v) => (v === "" ? undefined : v),
    z.string().email("Email inválido").optional()
  ),
  phone: z.string().optional(),
  address: z.string().optional(),
  contact_person: z.string().optional(),
  payment_terms: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// ------------------------------------------------------------------ component

interface SupplierFormProps {
  supplier?: Supplier;
  onClose: () => void;
}

export function SupplierForm({ supplier, onClose }: SupplierFormProps) {
  const isEditing = !!supplier;
  const createMutation = useCreateSupplier();
  const updateMutation = useUpdateSupplier();
  const isPending = createMutation.isPending || updateMutation.isPending;
  const error =
    createMutation.error || updateMutation.error
      ? getApiErrorMessage(createMutation.error ?? updateMutation.error)
      : null;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: supplier
      ? {
          name: supplier.name,
          tax_id: supplier.tax_id ?? "",
          email: supplier.email ?? "",
          phone: supplier.phone ?? "",
          address: supplier.address ?? "",
          contact_person: supplier.contact_person ?? "",
          payment_terms: supplier.payment_terms ?? "",
          notes: supplier.notes ?? "",
        }
      : {},
  });

  // Reset form when supplier prop changes
  useEffect(() => {
    if (supplier) {
      reset({
        name: supplier.name,
        tax_id: supplier.tax_id ?? "",
        email: supplier.email ?? "",
        phone: supplier.phone ?? "",
        address: supplier.address ?? "",
        contact_person: supplier.contact_person ?? "",
        payment_terms: supplier.payment_terms ?? "",
        notes: supplier.notes ?? "",
      });
    }
  }, [supplier, reset]);

  const onSubmit = async (values: FormValues) => {
    // Convert empty strings to null for optional fields
    const payload = Object.fromEntries(
      Object.entries(values).map(([k, v]) => [k, v === "" ? null : v])
    );

    if (isEditing) {
      await updateMutation.mutateAsync(
        { id: supplier.id, ...payload },
        { onSuccess: onClose }
      );
    } else {
      await createMutation.mutateAsync(payload as FormValues, {
        onSuccess: onClose,
      });
    }
  };

  return (
    // Backdrop
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? "Editar proveedor" : "Nuevo proveedor"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
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
            <input {...register("name")} placeholder="Nombre del proveedor" />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="CIF / NIF" error={errors.tax_id?.message}>
              <input {...register("tax_id")} placeholder="B12345678" />
            </Field>
            <Field label="Teléfono" error={errors.phone?.message}>
              <input {...register("phone")} placeholder="+34 600 000 000" />
            </Field>
          </div>

          <Field label="Email" error={errors.email?.message}>
            <input {...register("email")} type="email" placeholder="contacto@proveedor.com" />
          </Field>

          <Field label="Dirección" error={errors.address?.message}>
            <input {...register("address")} placeholder="Calle, número, ciudad" />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Persona de contacto" error={errors.contact_person?.message}>
              <input {...register("contact_person")} placeholder="Nombre y apellidos" />
            </Field>
            <Field label="Condiciones de pago" error={errors.payment_terms?.message}>
              <input {...register("payment_terms")} placeholder="30 días, contado..." />
            </Field>
          </div>

          <Field label="Notas" error={errors.notes?.message}>
            <textarea
              {...register("notes")}
              rows={3}
              placeholder="Observaciones internas..."
              className="resize-none"
            />
          </Field>
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
            type="submit"
            form="supplier-form"
            disabled={isPending}
            onClick={handleSubmit(onSubmit)}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {isPending ? "Guardando..." : isEditing ? "Guardar cambios" : "Crear proveedor"}
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
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {/* Inject shared input styles into the child */}
      {applyInputStyles(children, !!error)}
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

function applyInputStyles(child: React.ReactElement, hasError: boolean) {
  const base =
    "w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500";
  const border = hasError ? "border-red-400" : "border-gray-300";
  return {
    ...child,
    props: {
      ...child.props,
      className: cn(base, border, child.props.className),
    },
  };
}
