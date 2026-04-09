import { useState } from "react";
import { Routes, Route, useParams, useMatch, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/shared/utils/cn";
import { SupplierList } from "./SupplierList";
import { SupplierDetail } from "./SupplierDetail";
import { SupplierForm } from "./SupplierForm";

function SupplierDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  if (!id) return null;
  return (
    <>
      {/* Mobile back button */}
      <div className="lg:hidden border-b border-gray-100 px-4 py-2">
        <button
          onClick={() => navigate("/proveedores")}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft size={14} />
          Proveedores
        </button>
      </div>
      <SupplierDetail supplierId={id} />
    </>
  );
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
          "flex flex-col min-w-0 border-r border-gray-100",
          isDetailSelected
            ? "hidden lg:flex lg:w-[52%] lg:shrink-0"
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
          "flex-1 flex flex-col overflow-hidden min-w-0",
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
