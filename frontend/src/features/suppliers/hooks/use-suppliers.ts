import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  Supplier,
  SupplierCreatePayload,
  SupplierListResponse,
  SupplierUpdatePayload,
} from "../types";

// ------------------------------------------------------------------ query keys

const supplierKeys = {
  all: ["suppliers"] as const,
  lists: () => [...supplierKeys.all, "list"] as const,
  list: (filters: SupplierFilters) => [...supplierKeys.lists(), filters] as const,
  details: () => [...supplierKeys.all, "detail"] as const,
  detail: (id: string) => [...supplierKeys.details(), id] as const,
};

// ------------------------------------------------------------------ types

interface SupplierFilters {
  q?: string;
  is_active?: boolean;
  skip?: number;
  limit?: number;
}

// ------------------------------------------------------------------ queries

export function useSuppliers(filters: SupplierFilters = {}) {
  return useQuery({
    queryKey: supplierKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<SupplierListResponse>("/api/v1/suppliers", {
        params: filters,
      });
      return data;
    },
  });
}

export function useSupplier(id: string | null) {
  return useQuery({
    queryKey: supplierKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<Supplier>(`/api/v1/suppliers/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

// ------------------------------------------------------------------ mutations

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SupplierCreatePayload) => {
      const { data } = await apiClient.post<Supplier>("/api/v1/suppliers", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
    },
  });
}

export function useUpdateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: SupplierUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<Supplier>(
        `/api/v1/suppliers/${id}`,
        payload
      );
      return data;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      queryClient.invalidateQueries({ queryKey: supplierKeys.detail(updated.id) });
    },
  });
}

export function useDeactivateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/suppliers/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
    },
  });
}
