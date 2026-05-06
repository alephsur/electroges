import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  BudgetTemplate,
  BudgetTemplateCreatePayload,
  BudgetTemplateUpdatePayload,
} from '../types'
import { budgetKeys } from './use-budgets'

export const templateKeys = {
  all: ['budget-templates'] as const,
  lists: () => [...templateKeys.all, 'list'] as const,
  list: (q: string) => [...templateKeys.lists(), q] as const,
  detail: (id: string) => [...templateKeys.all, id] as const,
}

interface TemplateListResponse {
  items: BudgetTemplate[]
  total: number
}

export function useBudgetTemplates(q: string = '') {
  return useQuery({
    queryKey: templateKeys.list(q),
    queryFn: async () => {
      const { data } = await apiClient.get<TemplateListResponse>(
        '/api/v1/budget-templates',
        { params: q ? { q } : undefined },
      )
      return data
    },
  })
}

export function useBudgetTemplate(id: string | null) {
  return useQuery({
    queryKey: templateKeys.detail(id!),
    queryFn: async () => {
      const { data } = await apiClient.get<BudgetTemplate>(
        `/api/v1/budget-templates/${id}`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useCreateTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: BudgetTemplateCreatePayload) => {
      const { data } = await apiClient.post<BudgetTemplate>(
        '/api/v1/budget-templates',
        payload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
  })
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: BudgetTemplateUpdatePayload & { id: string }) => {
      const { data } = await apiClient.patch<BudgetTemplate>(
        `/api/v1/budget-templates/${id}`,
        payload,
      )
      return data
    },
    onSuccess: (_d, vars) => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(vars.id) })
    },
  })
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/budget-templates/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
  })
}

export function useApplyTemplate(budgetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      templateId,
      mode,
    }: {
      templateId: string
      mode: 'append' | 'replace'
    }) => {
      await apiClient.post(`/api/v1/budgets/${budgetId}/apply-template`, {
        template_id: templateId,
        mode,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) })
    },
  })
}

export function useSaveBudgetAsTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      budgetId,
      name,
      description,
    }: {
      budgetId: string
      name: string
      description?: string
    }) => {
      const params: Record<string, string> = { name }
      if (description) params.description = description
      const { data } = await apiClient.post<BudgetTemplate>(
        `/api/v1/budgets/${budgetId}/save-as-template`,
        null,
        { params },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
  })
}
