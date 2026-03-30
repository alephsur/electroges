import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  Budget,
  BudgetCreatePayload,
  BudgetFilters,
  BudgetFromVisitPayload,
  BudgetListResponse,
  BudgetUpdatePayload,
  BudgetVersionInfo,
  WorkOrderPreview,
} from '../types'

export const budgetKeys = {
  all: ['budgets'] as const,
  lists: () => [...budgetKeys.all, 'list'] as const,
  list: (filters: BudgetFilters) => [...budgetKeys.lists(), filters] as const,
  detail: (id: string) => [...budgetKeys.all, id] as const,
  versions: (id: string) => [...budgetKeys.all, id, 'versions'] as const,
  preview: (id: string) => [...budgetKeys.all, id, 'work-order-preview'] as const,
}

export function useBudgets(filters: BudgetFilters) {
  return useQuery({
    queryKey: budgetKeys.list(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<BudgetListResponse>('/api/v1/budgets', {
        params: filters,
      })
      return data
    },
  })
}

export function useBudget(id: string | null) {
  return useQuery({
    queryKey: budgetKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<Budget>(`/api/v1/budgets/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useBudgetVersions(id: string | null) {
  return useQuery({
    queryKey: budgetKeys.versions(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<BudgetVersionInfo[]>(
        `/api/v1/budgets/${id}/versions`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useWorkOrderPreview(id: string | null) {
  return useQuery({
    queryKey: budgetKeys.preview(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<WorkOrderPreview>(
        `/api/v1/budgets/${id}/work-order-preview`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useCreateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BudgetCreatePayload) => {
      const { data } = await apiClient.post<Budget>('/api/v1/budgets', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useCreateBudgetFromVisit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BudgetFromVisitPayload) => {
      const { data } = await apiClient.post<Budget>('/api/v1/budgets/from-visit', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useUpdateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }: BudgetUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<Budget>(`/api/v1/budgets/${id}`, payload)
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useSendBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<Budget>(`/api/v1/budgets/${id}/send`)
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useRejectBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, notes }: { id: string; notes?: string }) => {
      const { data } = await apiClient.post<Budget>(
        `/api/v1/budgets/${id}/reject`,
        null,
        { params: notes ? { notes } : undefined },
      )
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(vars.id) })
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useCreateNewVersion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<Budget>(`/api/v1/budgets/${id}/new-version`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}

export function useAcceptBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post(`/api/v1/budgets/${id}/accept`)
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() })
    },
  })
}
