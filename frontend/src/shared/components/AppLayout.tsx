import { useState, useEffect, useRef } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { useTenantBranding } from "@/features/admin/hooks/use-tenants";
import { ChangePasswordModal } from "@/features/auth/components/ChangePasswordModal";
import {
  LayoutDashboard, Users, MapPin, FileText,
  HardHat, Receipt, Package, Truck, LogOut,
  Menu, X, ChevronLeft, ChevronRight, ShieldCheck, CalendarDays, KeyRound,
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
  { to: "/calendario",    label: "Calendario",        icon: CalendarDays },
];

const ADMIN_ITEMS = [
  { to: "/admin/tenants", label: "Tenants", icon: ShieldCheck },
];

function resolveLogoUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  // /uploads/* are always relative paths: nginx proxies them in prod, Vite proxy in dev.
  return url;
}

export function AppLayout() {
  const { user, logout } = useAuthStore();
  const isSuperAdmin = user?.role === "superadmin";
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [logoError, setLogoError] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { data: branding } = useTenantBranding();
  const logoUrl = resolveLogoUrl(branding?.logo_url);

  useEffect(() => { setLogoError(false); }, [logoUrl]);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const link = (document.querySelector("link[rel~='icon']") as HTMLLinkElement)
      ?? Object.assign(document.createElement("link"), { rel: "icon" });
    if (!link.parentNode) document.head.appendChild(link);
    link.href = logoUrl && !logoError
      ? logoUrl
      : "/favicon.ico";
  }, [logoUrl, logoError]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
    {showChangePassword && (
      <ChangePasswordModal onClose={() => setShowChangePassword(false)} />
    )}
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
            logoUrl && !logoError ? (
              <img
                src={logoUrl}
                alt="Logo"
                className="mx-auto h-8 w-8 object-contain rounded"
                onError={() => setLogoError(true)}
              />
            ) : (
              <span className="mx-auto text-xl leading-none">⚡</span>
            )
          ) : logoUrl && !logoError ? (
            <div className="flex-1 min-w-0 flex items-center">
              <img
                src={logoUrl}
                alt={branding?.name ?? "Logo"}
                className="h-12 w-auto max-w-full object-contain rounded"
                onError={() => setLogoError(true)}
              />
            </div>
          ) : (
            <span className="flex-1 text-xl font-bold text-brand-700 truncate">
              ⚡ {branding?.name ?? "ElectroGes"}
            </span>
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

          {isSuperAdmin && (
            <>
              {!collapsed && (
                <p className="px-3 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
                  Administración
                </p>
              )}
              {collapsed && <div className="my-2 border-t border-gray-100" />}
              {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
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
            </>
          )}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-200 p-3 shrink-0 relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            title={collapsed ? user?.full_name ?? "Usuario" : undefined}
            className={cn(
              "w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 transition-colors",
              collapsed && "justify-center px-2"
            )}
          >
            <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center text-xs font-bold text-brand-700 shrink-0">
              {user?.full_name?.[0]?.toUpperCase() ?? "U"}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-medium text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
              </div>
            )}
          </button>

          {/* Dropdown menu */}
          {userMenuOpen && (
            <div className={cn(
              "absolute bottom-full mb-1 left-2 right-2 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-40",
              collapsed && "left-14 right-auto w-48 bottom-2"
            )}>
              <button
                onClick={() => { setUserMenuOpen(false); setShowChangePassword(true); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <KeyRound size={14} className="shrink-0 text-gray-400" />
                Cambiar contraseña
              </button>
              <div className="border-t border-gray-100 my-1" />
              <button
                onClick={() => { setUserMenuOpen(false); handleLogout(); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut size={14} className="shrink-0" />
                Cerrar sesión
              </button>
            </div>
          )}
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
          {logoUrl && !logoError ? (
            <img src={logoUrl} alt={branding?.name ?? "Logo"} className="h-9 w-auto max-w-[160px] object-contain rounded" onError={() => setLogoError(true)} />
          ) : (
            <span className="text-base font-bold text-brand-700">⚡ {branding?.name ?? "ElectroGes"}</span>
          )}
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="h-full p-4 md:p-6 max-w-screen-xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
    </>
  );
}
