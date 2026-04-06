import { Plus, Search } from "lucide-react";
import { useNavigate, useMatch } from "react-router-dom";
import { useSuppliers } from "../hooks/use-suppliers";
import { useSupplierStore } from "../store/supplier-store";
import { useDebounce } from "@/shared/hooks/use-debounce";
import { cn } from "@/shared/utils/cn";
import type { Supplier } from "../types";

interface SupplierListProps {
  onNew: () => void;
}

export function SupplierList({ onNew }: SupplierListProps) {
  const navigate = useNavigate();
  const match = useMatch("/proveedores/:id");
  const selectedId = match?.params.id ?? null;
  const {
    searchQuery,
    isActiveFilter,
    setSearchQuery,
    setIsActiveFilter,
  } = useSupplierStore();

  const debouncedQuery = useDebounce(searchQuery, 300);

  const { data, isLoading, error } = useSuppliers({
    q: debouncedQuery || undefined,
    is_active: isActiveFilter,
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por nombre o CIF..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Active / Inactive toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm">
            <ToggleBtn
              active={isActiveFilter}
              onClick={() => setIsActiveFilter(true)}
            >
              Activos
            </ToggleBtn>
            <ToggleBtn
              active={!isActiveFilter}
              onClick={() => setIsActiveFilter(false)}
            >
              Inactivos
            </ToggleBtn>
          </div>
        </div>

        <button
          onClick={onNew}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors shrink-0"
        >
          <Plus size={15} />
          Nuevo proveedor
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-gray-400">Cargando proveedores...</div>
        ) : error ? (
          <div className="py-16 text-center text-sm text-red-500">
            Error al cargar proveedores
          </div>
        ) : !data?.items.length ? (
          <div className="py-16 text-center text-sm text-gray-400">
            {debouncedQuery
              ? `Sin resultados para "${debouncedQuery}"`
              : isActiveFilter
              ? "No hay proveedores activos"
              : "No hay proveedores inactivos"}
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">CIF / NIF</th>
                  <th className="px-4 py-3 hidden md:table-cell">Contacto</th>
                  <th className="px-4 py-3 hidden lg:table-cell">Teléfono</th>
                  <th className="px-4 py-3 hidden lg:table-cell">Email</th>
                  <th className="px-4 py-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((supplier) => (
                  <SupplierRow
                    key={supplier.id}
                    supplier={supplier}
                    isSelected={selectedId === supplier.id}
                    onClick={() => navigate(`/proveedores/${supplier.id}`)}
                  />
                ))}
              </tbody>
            </table>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-gray-100 text-xs text-gray-400">
              {data.total} proveedor{data.total !== 1 ? "es" : ""}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ helpers

function SupplierRow({
  supplier,
  isSelected,
  onClick,
}: {
  supplier: Supplier;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "cursor-pointer transition-colors",
        isSelected ? "bg-brand-50" : "hover:bg-gray-50",
      )}
    >
      <td className="px-4 py-3 font-medium text-gray-900">{supplier.name}</td>
      <td className="px-4 py-3 text-gray-500">{supplier.tax_id ?? "—"}</td>
      <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
        {supplier.contact_person ?? "—"}
      </td>
      <td className="px-4 py-3 text-gray-500 hidden lg:table-cell">
        {supplier.phone ?? "—"}
      </td>
      <td className="px-4 py-3 text-gray-500 hidden lg:table-cell">
        {supplier.email ?? "—"}
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
            supplier.is_active
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          )}
        >
          {supplier.is_active ? "Activo" : "Inactivo"}
        </span>
      </td>
    </tr>
  );
}

function ToggleBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50"
      )}
    >
      {children}
    </button>
  );
}
