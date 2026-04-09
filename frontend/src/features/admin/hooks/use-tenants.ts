import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  CompanySettings,
  CompanySettingsUpdate,
  Tenant,
  TenantCreate,
  TenantUpdate,
  TenantUserInfo,
  TenantUserInvite,
  TenantUserUpdate,
} from "../types";

export interface TenantBranding {
  name: string;
  logo_url: string | null;
}

const BRANDING_KEY = "tenant-branding";

const QUERY_KEY = "tenants";

async function fetchTenants(): Promise<Tenant[]> {
  const { data } = await apiClient.get("/api/v1/tenants/");
  return data;
}

async function fetchTenant(id: string): Promise<Tenant> {
  const { data } = await apiClient.get(`/api/v1/tenants/${id}`);
  return data;
}

async function createTenant(payload: TenantCreate): Promise<Tenant> {
  const { data } = await apiClient.post("/api/v1/tenants/", payload);
  return data;
}

async function updateTenant(id: string, payload: TenantUpdate): Promise<Tenant> {
  const { data } = await apiClient.patch(`/api/v1/tenants/${id}`, payload);
  return data;
}

async function deactivateTenant(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/tenants/${id}`);
}

async function inviteUser(tenantId: string, payload: TenantUserInvite): Promise<TenantUserInfo> {
  const { data } = await apiClient.post(`/api/v1/tenants/${tenantId}/users`, payload);
  return data;
}

async function updateTenantUser(
  tenantId: string,
  userId: string,
  payload: TenantUserUpdate
): Promise<TenantUserInfo> {
  const { data } = await apiClient.patch(`/api/v1/tenants/${tenantId}/users/${userId}`, payload);
  return data;
}

async function deactivateTenantUser(tenantId: string, userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/tenants/${tenantId}/users/${userId}`);
}

async function resendInvitation(tenantId: string, userId: string): Promise<void> {
  await apiClient.post(`/api/v1/tenants/${tenantId}/users/${userId}/resend-invitation`);
}

async function fetchTenantBranding(): Promise<TenantBranding> {
  const { data } = await apiClient.get("/api/v1/tenants/branding");
  return data;
}

async function fetchTenantCompanySettings(tenantId: string): Promise<CompanySettings> {
  const { data } = await apiClient.get(`/api/v1/tenants/${tenantId}/company-settings`);
  return data;
}

async function updateTenantCompanySettings(tenantId: string, payload: CompanySettingsUpdate): Promise<CompanySettings> {
  const { data } = await apiClient.patch(`/api/v1/tenants/${tenantId}/company-settings`, payload);
  return data;
}

async function uploadTenantLogo(tenantId: string, file: File): Promise<Tenant> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(`/api/v1/tenants/${tenantId}/logo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export function useTenants() {
  return useQuery({ queryKey: [QUERY_KEY], queryFn: fetchTenants });
}

export function useTenant(id: string) {
  return useQuery({ queryKey: [QUERY_KEY, id], queryFn: () => fetchTenant(id) });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createTenant,
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useUpdateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TenantUpdate }) => updateTenant(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useDeactivateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deactivateTenant,
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useInviteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, data }: { tenantId: string; data: TenantUserInvite }) =>
      inviteUser(tenantId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useUpdateTenantUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      tenantId,
      userId,
      data,
    }: {
      tenantId: string;
      userId: string;
      data: TenantUserUpdate;
    }) => updateTenantUser(tenantId, userId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useDeactivateTenantUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, userId }: { tenantId: string; userId: string }) =>
      deactivateTenantUser(tenantId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useResendInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, userId }: { tenantId: string; userId: string }) =>
      resendInvitation(tenantId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QUERY_KEY] }),
  });
}

export function useTenantBranding() {
  return useQuery({
    queryKey: [BRANDING_KEY],
    queryFn: fetchTenantBranding,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTenantCompanySettings(tenantId: string | null) {
  return useQuery({
    queryKey: [QUERY_KEY, tenantId, "company-settings"],
    queryFn: () => fetchTenantCompanySettings(tenantId!),
    enabled: !!tenantId,
  });
}

export function useUpdateTenantCompanySettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, data }: { tenantId: string; data: CompanySettingsUpdate }) =>
      updateTenantCompanySettings(tenantId, data),
    onSuccess: (_, { tenantId }) => {
      qc.invalidateQueries({ queryKey: [QUERY_KEY, tenantId, "company-settings"] });
    },
  });
}

export function useUploadTenantLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tenantId, file }: { tenantId: string; file: File }) =>
      uploadTenantLogo(tenantId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [QUERY_KEY] });
      qc.invalidateQueries({ queryKey: [BRANDING_KEY] });
    },
  });
}
