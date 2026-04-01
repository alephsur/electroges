import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { LoginPage } from "@/features/auth/components/LoginPage";
import { AppLayout } from "@/shared/components/AppLayout";
import { SuppliersPage } from "@/features/suppliers/components/SuppliersPage";
import { InventoryPage } from "@/features/inventory/components/InventoryPage";
import { CustomersPage } from "@/features/customers/components/CustomersPage"
import { SiteVisitsPage } from "@/features/site-visits/components/SiteVisitsPage";
import { BudgetsPage } from "@/features/budgets/components/BudgetsPage"
import { WorkOrdersPage } from "@/features/work-orders/components/WorkOrdersPage";
import { InvoicingPage } from "@/features/invoicing/components/InvoicingPage";
import { DashboardPage } from "@/features/dashboard/components/DashboardPage";

// Placeholder page until each module is implemented
const ComingSoon = ({ title }: { title: string }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <h2 className="text-2xl font-semibold text-gray-700">{title}</h2>
      <p className="text-gray-400 mt-2">Módulo en desarrollo</p>
    </div>
  </div>
);

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <AppLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="clientes/*" element={<CustomersPage />} />
        <Route path="visitas/*" element={<SiteVisitsPage />} />
        <Route path="presupuestos/*" element={<BudgetsPage />} />
        <Route path="obras/*" element={<WorkOrdersPage />} />
        <Route path="facturacion/*" element={<InvoicingPage />} />
        <Route path="inventario/*" element={<InventoryPage />} />
        <Route path="proveedores/*" element={<SuppliersPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
