import { create } from 'zustand'
import type { WorkOrderStatus } from '../types'

type ActiveTab = 'resumen' | 'tareas' | 'materiales' | 'pedidos' | 'certificaciones' | 'albaranes' | 'notas'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface WorkOrderUIState {
  searchQuery: string
  statusFilter: WorkOrderStatus | null
  customerFilter: string | null
  activeTab: ActiveTab
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: WorkOrderStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useWorkOrderStore = create<WorkOrderUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  activeTab: 'resumen',
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setStatusFilter: (s) => set({ statusFilter: s, page: 1 }),
  setCustomerFilter: (id) => set({ customerFilter: id, page: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
