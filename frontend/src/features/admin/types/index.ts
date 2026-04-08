export type TenantUserRole = "admin" | "user";

export interface TenantUserInfo {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: TenantUserRole;
  invitation_expires_at: string | null;
}

// Kept as alias for backwards compatibility
export type TenantAdminInfo = TenantUserInfo;

export interface Tenant {
  id: string;
  name: string;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  logo_url: string | null;
  users: TenantUserInfo[];
}

export interface TenantCreate {
  name: string;
  tax_id?: string;
  address?: string;
  phone?: string;
  email?: string;
  admin_email: string;
  admin_full_name: string;
}

export interface TenantUpdate {
  name?: string;
  tax_id?: string;
  address?: string;
  phone?: string;
  email?: string;
  is_active?: boolean;
}

export interface TenantUserInvite {
  email: string;
  full_name: string;
  role: TenantUserRole;
}

export interface TenantUserUpdate {
  role?: TenantUserRole;
  is_active?: boolean;
}

export interface CompanySettings {
  company_name: string;
  tax_id: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  phone: string | null;
  email: string | null;
  bank_account: string | null;
  logo_path: string | null;
  general_conditions: string | null;
  default_tax_rate: string;
  default_validity_days: number;
}

export interface CompanySettingsUpdate {
  company_name?: string;
  tax_id?: string;
  address?: string;
  city?: string;
  postal_code?: string;
  phone?: string;
  email?: string;
  bank_account?: string;
  general_conditions?: string;
  default_tax_rate?: string;
  default_validity_days?: number;
}

export type InvitationStatus = "active" | "expired" | "activated";

export function getInvitationStatus(user: TenantUserInfo): InvitationStatus {
  if (user.is_active) return "activated";
  if (!user.invitation_expires_at) return "expired";
  return new Date(user.invitation_expires_at) > new Date() ? "active" : "expired";
}
