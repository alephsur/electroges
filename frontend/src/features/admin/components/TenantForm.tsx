import { useEffect } from "react";
import { useForm } from "react-hook-form";
import type { CompanySettings, CompanySettingsUpdate, Tenant, TenantCreate, TenantUpdate } from "../types";

interface CreateProps {
  mode: "create";
  onSubmit: (data: TenantCreate) => void;
  isLoading: boolean;
  onCancel: () => void;
}

interface EditProps {
  mode: "edit";
  tenant: Tenant;
  companySettings: CompanySettings | undefined;
  onSubmit: (tenant: TenantUpdate, company: CompanySettingsUpdate) => void;
  isLoading: boolean;
  onCancel: () => void;
}

type Props = CreateProps | EditProps;

type FormValues = {
  // Tenant fields
  name: string;
  tax_id: string;
  address: string;
  phone: string;
  email: string;
  // Admin user (create only)
  admin_email: string;
  admin_full_name: string;
  // Company settings (edit only)
  company_name: string;
  company_tax_id: string;
  company_address: string;
  company_city: string;
  company_postal_code: string;
  company_phone: string;
  company_email: string;
  bank_account: string;
  default_tax_rate: string;
  default_validity_days: string;
  general_conditions: string;
};

const INPUT_CLS =
  "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500";
const LABEL_CLS = "block text-sm font-medium text-gray-700 mb-1";

export function TenantForm(props: Props) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>();

  useEffect(() => {
    if (props.mode === "edit") {
      const cs = props.companySettings;
      reset({
        name: props.tenant.name,
        tax_id: props.tenant.tax_id ?? "",
        address: props.tenant.address ?? "",
        phone: props.tenant.phone ?? "",
        email: props.tenant.email ?? "",
        admin_email: "",
        admin_full_name: "",
        company_name: cs?.company_name ?? "",
        company_tax_id: cs?.tax_id ?? "",
        company_address: cs?.address ?? "",
        company_city: cs?.city ?? "",
        company_postal_code: cs?.postal_code ?? "",
        company_phone: cs?.phone ?? "",
        company_email: cs?.email ?? "",
        bank_account: cs?.bank_account ?? "",
        default_tax_rate: cs?.default_tax_rate ?? "21.00",
        default_validity_days: String(cs?.default_validity_days ?? 30),
        general_conditions: cs?.general_conditions ?? "",
      });
    }
  }, [
    props.mode,
    props.mode === "edit" ? props.tenant : null,
    props.mode === "edit" ? props.companySettings : null,
    reset,
  ]);

  const onSubmit = (values: FormValues) => {
    if (props.mode === "create") {
      props.onSubmit({
        name: values.name,
        tax_id: values.tax_id || undefined,
        address: values.address || undefined,
        phone: values.phone || undefined,
        email: values.email || undefined,
        admin_email: values.admin_email,
        admin_full_name: values.admin_full_name,
      });
    } else {
      const tenantData: TenantUpdate = {
        name: values.name,
        tax_id: values.tax_id || undefined,
        address: values.address || undefined,
        phone: values.phone || undefined,
        email: values.email || undefined,
      };
      const companyData: CompanySettingsUpdate = {
        company_name: values.company_name || undefined,
        tax_id: values.company_tax_id || undefined,
        address: values.company_address || undefined,
        city: values.company_city || undefined,
        postal_code: values.company_postal_code || undefined,
        phone: values.company_phone || undefined,
        email: values.company_email || undefined,
        bank_account: values.bank_account || undefined,
        default_tax_rate: values.default_tax_rate || undefined,
        default_validity_days: values.default_validity_days
          ? parseInt(values.default_validity_days, 10)
          : undefined,
        general_conditions: values.general_conditions || undefined,
      };
      props.onSubmit(tenantData, companyData);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* ── Tenant section ── */}
      <div>
        <p className="text-sm font-semibold text-gray-900 mb-3">Información del tenant</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className={LABEL_CLS}>
              Nombre <span className="text-red-500">*</span>
            </label>
            <input
              {...register("name", { required: "Requerido" })}
              className={INPUT_CLS}
              placeholder="Nombre de la empresa"
            />
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className={LABEL_CLS}>CIF / NIF</label>
            <input {...register("tax_id")} className={INPUT_CLS} placeholder="B12345678" />
          </div>

          <div>
            <label className={LABEL_CLS}>Teléfono</label>
            <input {...register("phone")} className={INPUT_CLS} placeholder="+34 600 000 000" />
          </div>

          <div>
            <label className={LABEL_CLS}>Email corporativo</label>
            <input {...register("email")} type="email" className={INPUT_CLS} placeholder="info@empresa.com" />
          </div>

          <div>
            <label className={LABEL_CLS}>Dirección</label>
            <input {...register("address")} className={INPUT_CLS} placeholder="Calle, número, ciudad" />
          </div>
        </div>
      </div>

      {/* ── Admin user (create only) ── */}
      {props.mode === "create" && (
        <div className="border-t border-gray-200 pt-4">
          <p className="text-sm font-semibold text-gray-900 mb-3">Usuario administrador</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className={LABEL_CLS}>
                Email <span className="text-red-500">*</span>
              </label>
              <input
                {...register("admin_email", { required: "Requerido" })}
                type="email"
                className={INPUT_CLS}
                placeholder="admin@empresa.com"
              />
              {errors.admin_email && (
                <p className="text-xs text-red-500 mt-1">{errors.admin_email.message}</p>
              )}
            </div>
            <div>
              <label className={LABEL_CLS}>
                Nombre completo <span className="text-red-500">*</span>
              </label>
              <input
                {...register("admin_full_name", { required: "Requerido" })}
                className={INPUT_CLS}
                placeholder="Nombre Apellidos"
              />
              {errors.admin_full_name && (
                <p className="text-xs text-red-500 mt-1">{errors.admin_full_name.message}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Company settings (edit only) ── */}
      {props.mode === "edit" && (
        <div className="border-t border-gray-200 pt-4">
          <p className="text-sm font-semibold text-gray-900 mb-1">Datos de empresa para documentos</p>
          <p className="text-xs text-gray-400 mb-3">
            Esta información aparece en presupuestos, facturas y albaranes.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={LABEL_CLS}>Nombre fiscal / razón social</label>
              <input
                {...register("company_name")}
                className={INPUT_CLS}
                placeholder="Nombre que aparece en los PDFs"
              />
            </div>

            <div>
              <label className={LABEL_CLS}>CIF / NIF fiscal</label>
              <input {...register("company_tax_id")} className={INPUT_CLS} placeholder="B12345678" />
            </div>

            <div>
              <label className={LABEL_CLS}>Teléfono (documentos)</label>
              <input {...register("company_phone")} className={INPUT_CLS} placeholder="+34 600 000 000" />
            </div>

            <div>
              <label className={LABEL_CLS}>Email (documentos)</label>
              <input {...register("company_email")} type="email" className={INPUT_CLS} placeholder="info@empresa.com" />
            </div>

            <div>
              <label className={LABEL_CLS}>Cuenta bancaria (IBAN)</label>
              <input {...register("bank_account")} className={INPUT_CLS} placeholder="ES00 0000 0000 0000 0000 0000" />
            </div>

            <div>
              <label className={LABEL_CLS}>Dirección fiscal</label>
              <input {...register("company_address")} className={INPUT_CLS} placeholder="Calle, número" />
            </div>

            <div>
              <label className={LABEL_CLS}>Ciudad</label>
              <input {...register("company_city")} className={INPUT_CLS} placeholder="Ciudad" />
            </div>

            <div>
              <label className={LABEL_CLS}>Código postal</label>
              <input {...register("company_postal_code")} className={INPUT_CLS} placeholder="00000" />
            </div>

            <div>
              <label className={LABEL_CLS}>IVA por defecto (%)</label>
              <input
                {...register("default_tax_rate")}
                type="number"
                step="0.01"
                min="0"
                max="100"
                className={INPUT_CLS}
                placeholder="21.00"
              />
            </div>

            <div>
              <label className={LABEL_CLS}>Validez presupuestos (días)</label>
              <input
                {...register("default_validity_days")}
                type="number"
                min="1"
                className={INPUT_CLS}
                placeholder="30"
              />
            </div>

            <div className="sm:col-span-2">
              <label className={LABEL_CLS}>Condiciones generales</label>
              <textarea
                {...register("general_conditions")}
                rows={3}
                className={INPUT_CLS}
                placeholder="Texto que aparece al pie de los documentos..."
              />
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={props.onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={props.isLoading}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {props.isLoading ? "Guardando..." : props.mode === "create" ? "Crear tenant" : "Guardar cambios"}
        </button>
      </div>
    </form>
  );
}
