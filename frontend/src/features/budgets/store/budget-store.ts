import { create } from 'zustand'
import type { BudgetStatus } from '../types'

type ActiveTab = 'lineas' | 'totales' | 'versiones'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface BudgetUIState {
  searchQuery: string
  statusFilter: BudgetStatus | null
  customerFilter: string | null
  showAllVersions: boolean
  activeTab: ActiveTab
  editingLineId: string | null
  showAddLineForm: boolean
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: BudgetStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setShowAllVersions: (v: boolean) => void
  setActiveTab: (tab: ActiveTab) => void
  setEditingLineId: (id: string | null) => void
  setShowAddLineForm: (show: boolean) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useBudgetStore = create<BudgetUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  showAllVersions: false,
  activeTab: 'lineas',
  editingLineId: null,
  showAddLineForm: false,
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setStatusFilter: (s) => set({ statusFilter: s, page: 1 }),
  setCustomerFilter: (id) => set({ customerFilter: id, page: 1 }),
  setShowAllVersions: (v) => set({ showAllVersions: v, page: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setEditingLineId: (id) => set({ editingLineId: id }),
  setShowAddLineForm: (show) => set({ showAddLineForm: show }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
