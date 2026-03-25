import { useState } from "react";
import { Routes, Route, useParams } from "react-router-dom";
import { SupplierList } from "./SupplierList";
import { SupplierDetail } from "./SupplierDetail";
import { SupplierForm } from "./SupplierForm";

// ------------------------------------------------------------------ list view

function SupplierListView() {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Proveedores</h1>
      <SupplierList onNew={() => setShowForm(true)} />
      {showForm && <SupplierForm onClose={() => setShowForm(false)} />}
    </div>
  );
}

// ------------------------------------------------------------------ detail view

function SupplierDetailView() {
  const { id } = useParams<{ id: string }>();
  if (!id) return null;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Proveedores</h1>
      <SupplierDetail supplierId={id} />
    </div>
  );
}

// ------------------------------------------------------------------ page (nested routes)

export function SuppliersPage() {
  return (
    <Routes>
      <Route index element={<SupplierListView />} />
      <Route path=":id" element={<SupplierDetailView />} />
    </Routes>
  );
}
