import { Mail, Phone, Plus, Search, User } from "lucide-react";
import { useNavigate, useMatch } from "react-router-dom";
import { useSuppliers } from "../hooks/use-suppliers";
import { useSupplierStore, PAGE_SIZE_OPTIONS } from "../store/supplier-store";
import type { PageSize } from "../store/supplier-store";
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
    page,
    pageSize,
    setSearchQuery,
    setIsActiveFilter,
    setPage,
    setPageSize,
  } = useSupplierStore();

  const debouncedQuery = useDebounce(searchQuery, 300);

  const { data, isLoading, error } = useSuppliers({
    q: debouncedQuery || undefined,
    is_active: isActiveFilter,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por nombre o CIF..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50"
            />
          </div>

          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
            <ToggleBtn active={isActiveFilter} onClick={() => setIsActiveFilter(true)}>
              Activos
            </ToggleBtn>
            <ToggleBtn active={!isActiveFilter} onClick={() => setIsActiveFilter(false)}>
              Inactivos
            </ToggleBtn>
          </div>
        </div>

        <button
          onClick={onNew}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors shrink-0"
        >
          <Plus size={14} />
          <span className="hidden sm:inline">Nuevo proveedor</span>
          <span className="sm:hidden">Nuevo</span>
        </button>
      </div>

      {/* List */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {/* Count header */}
        {data && (
          <div className="px-4 py-3 border-b border-gray-100">
            <span className="text-xs font-medium text-gray-500">{data.total} proveedores</span>
          </div>
        )}

        {isLoading ? (
          <div className="py-16 text-center text-sm text-gray-400">Cargando proveedores...</div>
        ) : error ? (
          <div className="py-16 text-center text-sm text-red-500">Error al cargar proveedores</div>
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
            <div className="divide-y divide-gray-50">
              {data.items.map((supplier) => (
                <SupplierRow
                  key={supplier.id}
                  supplier={supplier}
                  isSelected={selectedId === supplier.id}
                  onClick={() => navigate(`/proveedores/${supplier.id}`)}
                />
              ))}
            </div>

            {/* Pagination */}
            <div className="px-4 py-2 border-t border-gray-100 flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <span>Por página:</span>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <button
                    key={size}
                    onClick={() => setPageSize(size as PageSize)}
                    className={`rounded px-2 py-0.5 font-medium transition-colors ${
                      pageSize === size
                        ? "bg-gray-900 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>
                  {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, data.total)} de {data.total}
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(page - 1)}
                    disabled={page <= 1}
                    className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                  >
                    ‹
                  </button>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages}
                    className="rounded px-2 py-0.5 bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                  >
                    ›
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ row

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
    <div
      onClick={onClick}
      className={cn(
        "flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors",
        isSelected ? "bg-brand-50" : "hover:bg-gray-50",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-full shrink-0 text-sm font-semibold",
          isSelected ? "bg-brand-200 text-brand-800" : "bg-gray-100 text-gray-600",
        )}
      >
        {supplier.name.charAt(0).toUpperCase()}
      </div>

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-900 truncate">
            {supplier.name}
          </span>
          {supplier.tax_id && (
            <span className="text-xs text-gray-400 shrink-0">{supplier.tax_id}</span>
          )}
          {!supplier.is_active && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 shrink-0">
              Inactivo
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          {supplier.contact_person && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <User size={10} />
              {supplier.contact_person}
            </span>
          )}
          {supplier.phone && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <Phone size={10} />
              {supplier.phone}
            </span>
          )}
          {supplier.email && (
            <span className="flex items-center gap-1 text-xs text-gray-400 truncate">
              <Mail size={10} className="shrink-0" />
              {supplier.email}
            </span>
          )}
        </div>
      </div>

      {/* Payment terms */}
      {supplier.payment_terms && (
        <div className="hidden lg:block text-xs text-gray-400 shrink-0 max-w-[140px] truncate text-right">
          {supplier.payment_terms}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ toggle

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
        active ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50",
      )}
    >
      {children}
    </button>
  );
}
