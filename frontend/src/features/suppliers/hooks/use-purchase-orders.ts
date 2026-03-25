import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  PurchaseOrder,
  PurchaseOrderCreatePayload,
  PurchaseOrderListResponse,
  PurchaseOrderUpdatePayload,
} from "../types";

// ------------------------------------------------------------------ query keys

export const purchaseOrderKeys = {
  all: ["purchase-orders"] as const,
  bySupplier: (supplierId: string) =>
    [...purchaseOrderKeys.all, "supplier", supplierId] as const,
  detail: (supplierId: string, orderId: string) =>
    [...purchaseOrderKeys.bySupplier(supplierId), orderId] as const,
};

// ------------------------------------------------------------------ queries

export function usePurchaseOrders(
  supplierId: string | null,
  params: { status?: string; skip?: number; limit?: number } = {}
) {
  return useQuery({
    queryKey: [...purchaseOrderKeys.bySupplier(supplierId!), params],
    queryFn: async () => {
      const { data } = await apiClient.get<PurchaseOrderListResponse>(
        `/api/v1/suppliers/${supplierId}/purchase-orders`,
        { params }
      );
      return data;
    },
    enabled: !!supplierId,
  });
}

export function usePurchaseOrder(supplierId: string | null, orderId: string | null) {
  return useQuery({
    queryKey: purchaseOrderKeys.detail(supplierId!, orderId!),
    queryFn: async () => {
      const { data } = await apiClient.get<PurchaseOrder>(
        `/api/v1/suppliers/${supplierId}/purchase-orders/${orderId}`
      );
      return data;
    },
    enabled: !!supplierId && !!orderId,
  });
}

// ------------------------------------------------------------------ mutations

export function useCreatePurchaseOrder(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PurchaseOrderCreatePayload) => {
      const { data } = await apiClient.post<PurchaseOrder>(
        `/api/v1/suppliers/${supplierId}/purchase-orders`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: purchaseOrderKeys.bySupplier(supplierId),
      });
    },
  });
}

export function useUpdatePurchaseOrder(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      orderId,
      ...payload
    }: PurchaseOrderUpdatePayload & { orderId: string }) => {
      const { data } = await apiClient.patch<PurchaseOrder>(
        `/api/v1/suppliers/${supplierId}/purchase-orders/${orderId}`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: purchaseOrderKeys.bySupplier(supplierId),
      });
    },
  });
}

export function useReceivePurchaseOrder(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      const { data } = await apiClient.post<PurchaseOrder>(
        `/api/v1/suppliers/${supplierId}/purchase-orders/${orderId}/receive`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: purchaseOrderKeys.bySupplier(supplierId),
      });
    },
  });
}

export function useCancelPurchaseOrder(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      const { data } = await apiClient.post<PurchaseOrder>(
        `/api/v1/suppliers/${supplierId}/purchase-orders/${orderId}/cancel`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: purchaseOrderKeys.bySupplier(supplierId),
      });
    },
  });
}
