import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  InventoryItem,
  InventoryItemCreatePayload,
  InventoryItemListResponse,
} from "../types";

// ------------------------------------------------------------------ query keys

export const inventoryItemKeys = {
  all: ["inventory-items"] as const,
  bySupplier: (supplierId: string) =>
    [...inventoryItemKeys.all, "supplier", supplierId] as const,
};

// ------------------------------------------------------------------ queries

export function useSupplierInventoryItems(
  supplierId: string | null,
  params: { is_active?: boolean; skip?: number; limit?: number } = {}
) {
  return useQuery({
    queryKey: [...inventoryItemKeys.bySupplier(supplierId!), params],
    queryFn: async () => {
      const { data } = await apiClient.get<InventoryItemListResponse>(
        `/api/v1/suppliers/${supplierId}/inventory-items`,
        { params }
      );
      return data;
    },
    enabled: !!supplierId,
  });
}

// ------------------------------------------------------------------ mutations

export function useCreateSupplierInventoryItem(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: InventoryItemCreatePayload) => {
      const { data } = await apiClient.post<InventoryItem>(
        `/api/v1/suppliers/${supplierId}/inventory-items`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: inventoryItemKeys.bySupplier(supplierId),
      });
    },
  });
}
