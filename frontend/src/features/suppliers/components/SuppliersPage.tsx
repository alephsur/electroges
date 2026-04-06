import { useState } from "react";
import { Routes, Route, useParams, useMatch } from "react-router-dom";
import { cn } from "@/shared/utils/cn";
import { SupplierList } from "./SupplierList";
import { SupplierDetail } from "./SupplierDetail";
import { SupplierForm } from "./SupplierForm";

function SupplierDetailRoute() {
  const { id } = useParams<{ id: string }>();
  if (!id) return null;
  return <SupplierDetail supplierId={id} />;
}

export function SuppliersPage() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const detailMatch = useMatch("/proveedores/:id");
  const isDetailSelected = !!detailMatch;

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — list */}
      <div
        className={cn(
          "flex flex-col min-w-0",
          isDetailSelected
            ? "hidden lg:flex lg:w-80 lg:shrink-0 lg:border-r lg:border-gray-100"
            : "flex flex-1",
        )}
      >
        <div className="flex-1 overflow-auto p-4">
          <SupplierList onNew={() => setShowCreateForm(true)} />
        </div>
      </div>

      {/* Right panel — detail */}
      <div
        className={cn(
          "flex-1 flex flex-col overflow-hidden min-w-0 p-4",
          !isDetailSelected && "hidden lg:flex",
        )}
      >
        <Routes>
          <Route
            index
            element={
              <div className="flex h-full items-center justify-center text-sm text-gray-400">
                Selecciona un proveedor para ver el detalle
              </div>
            }
          />
          <Route path=":id" element={<SupplierDetailRoute />} />
        </Routes>
      </div>

      {showCreateForm && (
        <SupplierForm onClose={() => setShowCreateForm(false)} />
      )}
    </div>
  );
}
