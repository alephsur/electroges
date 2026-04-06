import { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/features/auth/store/auth-store";
import {
  LayoutDashboard, Users, MapPin, FileText,
  HardHat, Receipt, Package, Truck, LogOut,
  Menu, X, ChevronLeft, ChevronRight,
} from "lucide-react";
import { cn } from "@/shared/utils/cn";

const NAV_ITEMS = [
  { to: "/dashboard",     label: "Dashboard",         icon: LayoutDashboard },
  { to: "/clientes",      label: "Clientes",          icon: Users },
  { to: "/visitas",       label: "Visitas Técnicas",  icon: MapPin },
  { to: "/presupuestos",  label: "Presupuestos",      icon: FileText },
  { to: "/obras",         label: "Obras",             icon: HardHat },
  { to: "/facturacion",   label: "Facturación",       icon: Receipt },
  { to: "/inventario",    label: "Inventario",        icon: Package },
  { to: "/proveedores",   label: "Proveedores",       icon: Truck },
];

export function AppLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex flex-col bg-white border-r border-gray-200",
          "transition-[width,transform] duration-200 ease-in-out",
          // Mobile: slide-in drawer
          "md:relative md:translate-x-0",
          mobileOpen ? "translate-x-0 w-64" : "-translate-x-full",
          // Desktop: collapsible icon rail
          collapsed ? "md:w-16" : "md:w-60",
        )}
      >
        {/* Logo row */}
        <div className="h-16 flex items-center px-4 border-b border-gray-200 shrink-0 gap-2">
          {collapsed ? (
            <span className="mx-auto text-xl leading-none">⚡</span>
          ) : (
            <span className="flex-1 text-xl font-bold text-brand-700 truncate">⚡ ElectroGes</span>
          )}
          {/* Mobile close button */}
          <button
            onClick={() => setMobileOpen(false)}
            className="shrink-0 p-1 rounded-md text-gray-400 hover:text-gray-600 md:hidden"
          >
            <X size={18} />
          </button>
          {/* Desktop collapse toggle */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="shrink-0 p-1 rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-600 hidden md:flex items-center justify-center"
          >
            {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  collapsed && "justify-center px-2",
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )
              }
            >
              <Icon size={17} className="shrink-0" />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-200 p-3 shrink-0">
          {!collapsed && (
            <div className="flex items-center gap-2 px-2 py-1 mb-1">
              <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center text-xs font-bold text-brand-700 shrink-0">
                {user?.full_name?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            title={collapsed ? "Cerrar sesión" : undefined}
            className={cn(
              "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors",
              collapsed && "justify-center px-2"
            )}
          >
            <LogOut size={15} />
            {!collapsed && "Cerrar sesión"}
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100"
          >
            <Menu size={20} />
          </button>
          <span className="text-base font-bold text-brand-700">⚡ ElectroGes</span>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="h-full p-4 md:p-6 max-w-screen-xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
