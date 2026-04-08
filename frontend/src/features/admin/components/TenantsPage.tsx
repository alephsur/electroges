import { useRef, useState } from "react";
import {
  Building2, Plus, Pencil, Trash2, MailCheck, MailX, RefreshCw,
  CheckCircle2, Clock, XCircle, ChevronDown, ChevronUp, UserPlus,
  Shield, User, ImagePlus,
} from "lucide-react";
import { cn } from "@/shared/utils/cn";
import {
  useTenants,
  useCreateTenant,
  useUpdateTenant,
  useDeactivateTenant,
  useResendInvitation,
  useInviteUser,
  useUpdateTenantUser,
  useDeactivateTenantUser,
  useUploadTenantLogo,
  useTenantCompanySettings,
  useUpdateTenantCompanySettings,
} from "../hooks/use-tenants";
import { TenantForm } from "./TenantForm";
import {
  getInvitationStatus,
  type CompanySettingsUpdate,
  type Tenant,
  type TenantUpdate,
  type TenantUserInfo,
  type TenantUserRole,
  type InvitationStatus,
} from "../types";

// ── Modal ─────────────────────────────────────────────────────────────────────

function Modal({ title, children, onClose }: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  );
}

// ── Invitation badge ──────────────────────────────────────────────────────────

function InvitationBadge({ status }: { status: InvitationStatus }) {
  if (status === "activated") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
        <CheckCircle2 size={11} /> Activado
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
        <Clock size={11} /> Invitación pendiente
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-full px-2 py-0.5">
      <XCircle size={11} /> Invitación expirada
    </span>
  );
}

// ── Role badge ────────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: TenantUserRole }) {
  if (role === "admin") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-full px-2 py-0.5">
        <Shield size={10} /> Admin
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-600 bg-gray-100 border border-gray-200 rounded-full px-2 py-0.5">
      <User size={10} /> Usuario
    </span>
  );
}

// ── Invite user form ──────────────────────────────────────────────────────────

function InviteUserForm({
  onSubmit,
  onCancel,
  isLoading,
}: {
  onSubmit: (data: { email: string; full_name: string; role: TenantUserRole }) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<TenantUserRole>("user");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ email, full_name: fullName, role });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
        <input
          type="text"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="Nombre del usuario"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="usuario@empresa.com"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as TenantUserRole)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
        >
          <option value="user">Usuario</option>
          <option value="admin">Administrador</option>
        </select>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50"
        >
          {isLoading ? "Enviando..." : "Enviar invitación"}
        </button>
      </div>
    </form>
  );
}

// ── Logo uploader ─────────────────────────────────────────────────────────────

function LogoUploader({
  tenant,
  onUpload,
  isUploading,
}: {
  tenant: Tenant;
  onUpload: (tenantId: string, file: File) => void;
  isUploading: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(tenant.id, file);
    // reset so the same file can be re-selected
    e.target.value = "";
  };

  const logoSrc = tenant.logo_url?.startsWith("/uploads")
    ? `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}${tenant.logo_url}`
    : tenant.logo_url;

  return (
    <div className="flex items-center gap-3">
      {logoSrc ? (
        <img
          src={logoSrc}
          alt="Logo actual"
          className="h-10 w-auto max-w-[100px] object-contain rounded border border-gray-200 bg-white p-1"
        />
      ) : (
        <div className="h-10 w-16 rounded border border-dashed border-gray-300 flex items-center justify-center text-gray-300">
          <ImagePlus size={18} />
        </div>
      )}
      <div>
        <button
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className="text-xs font-medium text-brand-700 border border-brand-200 bg-brand-50 hover:bg-brand-100 rounded-lg px-2.5 py-1.5 transition-colors disabled:opacity-50"
        >
          {isUploading ? (
            <span className="flex items-center gap-1"><RefreshCw size={11} className="animate-spin" /> Subiendo...</span>
          ) : tenant.logo_url ? (
            "Cambiar logo"
          ) : (
            "Subir logo"
          )}
        </button>
        <p className="text-[10px] text-gray-400 mt-0.5">PNG, JPG, SVG · máx. 5 MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}

// ── User row in expanded panel ────────────────────────────────────────────────

function UserRow({
  user,
  tenantId,
  onResendInvitation,
  resendingUserId,
  onRoleChange,
  onDeactivate,
}: {
  user: TenantUserInfo;
  tenantId: string;
  onResendInvitation: (tenantId: string, userId: string) => void;
  resendingUserId: string | null;
  onRoleChange: (userId: string, role: TenantUserRole) => void;
  onDeactivate: (userId: string) => void;
}) {
  const invStatus = getInvitationStatus(user);
  const expiresLabel = user.invitation_expires_at
    ? new Date(user.invitation_expires_at).toLocaleString("es-ES", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit",
      })
    : null;

  return (
    <div className={cn(
      "rounded-lg border px-3 py-2.5 space-y-2",
      user.is_active ? "border-gray-200 bg-white" : "border-gray-100 bg-gray-50 opacity-60"
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-800">{user.full_name}</span>
            <RoleBadge role={user.role} />
            <InvitationBadge status={invStatus} />
            {!user.is_active && invStatus === "activated" && (
              <span className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">Desactivado</span>
            )}
          </div>
          <p className="text-xs text-gray-400">{user.email}</p>
          {invStatus !== "activated" && expiresLabel && (
            <p className="text-xs text-gray-400">
              {invStatus === "active" ? "Expira:" : "Expiró:"} {expiresLabel}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Role toggle */}
          {user.is_active && (
            <button
              onClick={() => onRoleChange(user.id, user.role === "admin" ? "user" : "admin")}
              className="text-xs text-gray-500 hover:text-brand-600 border border-gray-200 hover:border-brand-200 rounded-lg px-2 py-1 transition-colors whitespace-nowrap"
              title={user.role === "admin" ? "Cambiar a Usuario" : "Cambiar a Admin"}
            >
              {user.role === "admin" ? "→ Usuario" : "→ Admin"}
            </button>
          )}

          {/* Resend invitation */}
          {invStatus !== "activated" && (
            <button
              onClick={() => onResendInvitation(tenantId, user.id)}
              disabled={resendingUserId === user.id}
              className={cn(
                "flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-lg border transition-colors flex-shrink-0",
                invStatus === "active"
                  ? "text-amber-700 border-amber-200 bg-amber-50 hover:bg-amber-100"
                  : "text-brand-700 border-brand-200 bg-brand-50 hover:bg-brand-100",
                resendingUserId === user.id && "opacity-50 cursor-not-allowed"
              )}
              title={invStatus === "active" ? "Reenviar invitación" : "Nueva invitación"}
            >
              {resendingUserId === user.id ? (
                <RefreshCw size={11} className="animate-spin" />
              ) : invStatus === "active" ? (
                <MailCheck size={11} />
              ) : (
                <MailX size={11} />
              )}
            </button>
          )}

          {/* Deactivate */}
          {user.is_active && (
            <button
              onClick={() => onDeactivate(user.id)}
              className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Desactivar usuario"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Tenant card ───────────────────────────────────────────────────────────────

function TenantCard({
  tenant,
  onEdit,
  onDeactivate,
  onResendInvitation,
  resendingUserId,
  onInviteUser,
  onUserRoleChange,
  onUserDeactivate,
  onLogoUpload,
  uploadingLogoTenantId,
}: {
  tenant: Tenant;
  onEdit: (t: Tenant) => void;
  onDeactivate: (t: Tenant) => void;
  onResendInvitation: (tenantId: string, userId: string) => void;
  resendingUserId: string | null;
  onInviteUser: (tenantId: string) => void;
  onUserRoleChange: (tenantId: string, userId: string, role: TenantUserRole) => void;
  onUserDeactivate: (tenantId: string, userId: string) => void;
  onLogoUpload: (tenantId: string, file: File) => void;
  uploadingLogoTenantId: string | null;
}) {
  const [expanded, setExpanded] = useState(false);

  const summaryUser = tenant.users[0] ?? null;
  const invStatus = summaryUser ? getInvitationStatus(summaryUser) : null;

  return (
    <div className={cn(
      "bg-white border rounded-xl overflow-hidden transition-all",
      tenant.is_active ? "border-gray-200" : "border-gray-200 opacity-60"
    )}>
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center">
          <Building2 size={18} className="text-brand-600" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 truncate">{tenant.name}</span>
            {!tenant.is_active && (
              <span className="text-xs font-medium text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">
                Inactivo
              </span>
            )}
            <span className="text-xs text-gray-400">
              {tenant.users.length} usuario{tenant.users.length !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5 flex-wrap">
            {tenant.tax_id && <span>{tenant.tax_id}</span>}
            {tenant.email && <span>{tenant.email}</span>}
            {tenant.phone && <span>{tenant.phone}</span>}
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => onEdit(tenant)}
            className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
            title="Editar"
          >
            <Pencil size={14} />
          </button>
          {tenant.is_active && (
            <button
              onClick={() => onDeactivate(tenant)}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Desactivar tenant"
            >
              <Trash2 size={14} />
            </button>
          )}
          <button
            onClick={() => setExpanded((e) => !e)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title={expanded ? "Ocultar usuarios" : "Ver usuarios"}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Summary line */}
      {summaryUser && !expanded && (
        <div className="flex items-center gap-2 px-4 pb-3 -mt-1">
          <div className="w-5 shrink-0" />
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500">{summaryUser.full_name}</span>
            <span className="text-xs text-gray-400">·</span>
            <RoleBadge role={summaryUser.role} />
            <span className="text-xs text-gray-400">·</span>
            {invStatus && <InvitationBadge status={invStatus} />}
          </div>
        </div>
      )}

      {/* Expanded panel */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 space-y-4">
          {/* Logo section */}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Logo</p>
            <LogoUploader
              tenant={tenant}
              onUpload={onLogoUpload}
              isUploading={uploadingLogoTenantId === tenant.id}
            />
          </div>

          {/* Users section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Usuarios del tenant
              </p>
              {tenant.is_active && (
                <button
                  onClick={() => onInviteUser(tenant.id)}
                  className="flex items-center gap-1.5 text-xs font-medium text-brand-700 border border-brand-200 bg-brand-50 hover:bg-brand-100 rounded-lg px-2.5 py-1.5 transition-colors"
                >
                  <UserPlus size={12} />
                  Añadir usuario
                </button>
              )}
            </div>

            {tenant.users.length === 0 ? (
              <p className="text-xs text-gray-400">Sin usuarios registrados.</p>
            ) : (
              <div className="space-y-2">
                {tenant.users.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    tenantId={tenant.id}
                    onResendInvitation={onResendInvitation}
                    resendingUserId={resendingUserId}
                    onRoleChange={(userId, role) => onUserRoleChange(tenant.id, userId, role)}
                    onDeactivate={(userId) => onUserDeactivate(tenant.id, userId)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Confirm dialog ────────────────────────────────────────────────────────────

function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  isLoading,
  danger = true,
}: {
  title: string;
  message: React.ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
  danger?: boolean;
}) {
  return (
    <Modal title={title} onClose={onCancel}>
      <p className="text-sm text-gray-600 mb-4">{message}</p>
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className={cn(
            "px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-50",
            danger ? "bg-red-600 hover:bg-red-700" : "bg-brand-600 hover:bg-brand-700"
          )}
        >
          {isLoading ? "..." : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function TenantsPage() {
  const { data: tenants = [], isLoading, error } = useTenants();
  const createMutation = useCreateTenant();
  const updateMutation = useUpdateTenant();
  const updateCompanyMutation = useUpdateTenantCompanySettings();
  const deactivateMutation = useDeactivateTenant();
  const resendMutation = useResendInvitation();
  const inviteUserMutation = useInviteUser();
  const updateUserMutation = useUpdateTenantUser();
  const deactivateUserMutation = useDeactivateTenantUser();
  const uploadLogoMutation = useUploadTenantLogo();

  const [showCreate, setShowCreate] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);

  const { data: editingCompanySettings } = useTenantCompanySettings(editingTenant?.id ?? null);
  const [confirmTenant, setConfirmTenant] = useState<Tenant | null>(null);
  const [resendingUserId, setResendingUserId] = useState<string | null>(null);
  const [invitingTenantId, setInvitingTenantId] = useState<string | null>(null);
  const [confirmUserDeactivate, setConfirmUserDeactivate] = useState<{ tenantId: string; userId: string } | null>(null);
  const [uploadingLogoTenantId, setUploadingLogoTenantId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "ok" | "error"; msg: string } | null>(null);

  const showFeedback = (type: "ok" | "error", msg: string) => {
    setFeedback({ type, msg });
    setTimeout(() => setFeedback(null), 3500);
  };

  const handleCreate = async (data: Parameters<typeof createMutation.mutateAsync>[0]) => {
    try {
      await createMutation.mutateAsync(data);
      setShowCreate(false);
      showFeedback("ok", "Tenant creado. Se ha enviado la invitación al administrador.");
    } catch {
      showFeedback("error", "Error al crear el tenant.");
    }
  };

  const handleUpdate = async (tenantData: TenantUpdate, companyData: CompanySettingsUpdate) => {
    if (!editingTenant) return;
    try {
      await Promise.all([
        updateMutation.mutateAsync({ id: editingTenant.id, data: tenantData }),
        updateCompanyMutation.mutateAsync({ tenantId: editingTenant.id, data: companyData }),
      ]);
      setEditingTenant(null);
      showFeedback("ok", "Tenant actualizado correctamente.");
    } catch {
      showFeedback("error", "Error al actualizar el tenant.");
    }
  };

  const handleDeactivateTenant = async () => {
    if (!confirmTenant) return;
    try {
      await deactivateMutation.mutateAsync(confirmTenant.id);
      setConfirmTenant(null);
      showFeedback("ok", "Tenant desactivado.");
    } catch {
      showFeedback("error", "Error al desactivar el tenant.");
    }
  };

  const handleResend = async (tenantId: string, userId: string) => {
    setResendingUserId(userId);
    try {
      await resendMutation.mutateAsync({ tenantId, userId });
      showFeedback("ok", "Invitación reenviada correctamente.");
    } catch {
      showFeedback("error", "Error al reenviar la invitación.");
    } finally {
      setResendingUserId(null);
    }
  };

  const handleInviteUser = async (data: { email: string; full_name: string; role: TenantUserRole }) => {
    if (!invitingTenantId) return;
    try {
      await inviteUserMutation.mutateAsync({ tenantId: invitingTenantId, data });
      setInvitingTenantId(null);
      showFeedback("ok", "Invitación enviada correctamente.");
    } catch {
      showFeedback("error", "Error al invitar al usuario.");
    }
  };

  const handleUserRoleChange = async (tenantId: string, userId: string, role: TenantUserRole) => {
    try {
      await updateUserMutation.mutateAsync({ tenantId, userId, data: { role } });
      showFeedback("ok", "Rol actualizado correctamente.");
    } catch {
      showFeedback("error", "Error al actualizar el rol.");
    }
  };

  const handleUserDeactivate = async () => {
    if (!confirmUserDeactivate) return;
    try {
      await deactivateUserMutation.mutateAsync(confirmUserDeactivate);
      setConfirmUserDeactivate(null);
      showFeedback("ok", "Usuario desactivado.");
    } catch {
      showFeedback("error", "Error al desactivar el usuario.");
    }
  };

  const handleLogoUpload = async (tenantId: string, file: File) => {
    setUploadingLogoTenantId(tenantId);
    try {
      await uploadLogoMutation.mutateAsync({ tenantId, file });
      showFeedback("ok", "Logo actualizado correctamente.");
    } catch {
      showFeedback("error", "Error al subir el logo.");
    } finally {
      setUploadingLogoTenantId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Gestión de Tenants</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {tenants.length} tenant{tenants.length !== 1 ? "s" : ""} registrado
            {tenants.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
        >
          <Plus size={15} />
          Nuevo tenant
        </button>
      </div>

      {/* Feedback toast */}
      {feedback && (
        <div
          className={cn(
            "fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium",
            feedback.type === "ok"
              ? "bg-green-600 text-white"
              : "bg-red-600 text-white"
          )}
        >
          {feedback.msg}
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="text-sm text-gray-400 py-10 text-center">Cargando tenants...</div>
      ) : error ? (
        <div className="text-sm text-red-500 py-10 text-center">Error al cargar los tenants.</div>
      ) : tenants.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Building2 size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No hay tenants registrados.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 text-sm text-brand-600 hover:underline"
          >
            Crear el primer tenant
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {tenants.map((tenant) => (
            <TenantCard
              key={tenant.id}
              tenant={tenant}
              onEdit={setEditingTenant}
              onDeactivate={setConfirmTenant}
              onResendInvitation={handleResend}
              resendingUserId={resendingUserId}
              onInviteUser={setInvitingTenantId}
              onUserRoleChange={handleUserRoleChange}
              onUserDeactivate={(tenantId, userId) => setConfirmUserDeactivate({ tenantId, userId })}
              onLogoUpload={handleLogoUpload}
              uploadingLogoTenantId={uploadingLogoTenantId}
            />
          ))}
        </div>
      )}

      {/* Create tenant modal */}
      {showCreate && (
        <Modal title="Nuevo tenant" onClose={() => setShowCreate(false)}>
          <TenantForm
            mode="create"
            onSubmit={handleCreate}
            isLoading={createMutation.isPending}
            onCancel={() => setShowCreate(false)}
          />
        </Modal>
      )}

      {/* Edit tenant modal */}
      {editingTenant && (
        <Modal title={`Editar — ${editingTenant.name}`} onClose={() => setEditingTenant(null)}>
          <TenantForm
            mode="edit"
            tenant={editingTenant}
            companySettings={editingCompanySettings}
            onSubmit={handleUpdate}
            isLoading={updateMutation.isPending || updateCompanyMutation.isPending}
            onCancel={() => setEditingTenant(null)}
          />
        </Modal>
      )}

      {/* Confirm deactivate tenant */}
      {confirmTenant && (
        <ConfirmDialog
          title="Desactivar tenant"
          message={
            <>
              ¿Desactivar el tenant <strong>{confirmTenant.name}</strong>? Los usuarios del tenant
              no podrán acceder al sistema. Esta acción puede revertirse editando el tenant.
            </>
          }
          confirmLabel="Desactivar"
          onConfirm={handleDeactivateTenant}
          onCancel={() => setConfirmTenant(null)}
          isLoading={deactivateMutation.isPending}
        />
      )}

      {/* Invite user modal */}
      {invitingTenantId && (
        <Modal title="Añadir usuario al tenant" onClose={() => setInvitingTenantId(null)}>
          <InviteUserForm
            onSubmit={handleInviteUser}
            onCancel={() => setInvitingTenantId(null)}
            isLoading={inviteUserMutation.isPending}
          />
        </Modal>
      )}

      {/* Confirm deactivate user */}
      {confirmUserDeactivate && (
        <ConfirmDialog
          title="Desactivar usuario"
          message="¿Desactivar este usuario? No podrá acceder al sistema. El tenant y el resto de usuarios no se verán afectados."
          confirmLabel="Desactivar"
          onConfirm={handleUserDeactivate}
          onCancel={() => setConfirmUserDeactivate(null)}
          isLoading={deactivateUserMutation.isPending}
        />
      )}
    </div>
  );
}
