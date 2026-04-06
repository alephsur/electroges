import { create } from 'zustand'
import type { BudgetStatus } from '../types'

type ActiveTab = 'lineas' | 'totales' | 'versiones'

interface BudgetUIState {
  searchQuery: string
  statusFilter: BudgetStatus | null
  customerFilter: string | null
  showAllVersions: boolean
  activeTab: ActiveTab
  editingLineId: string | null
  showAddLineForm: boolean

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: BudgetStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setShowAllVersions: (v: boolean) => void
  setActiveTab: (tab: ActiveTab) => void
  setEditingLineId: (id: string | null) => void
  setShowAddLineForm: (show: boolean) => void
}

export const useBudgetStore = create<BudgetUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  showAllVersions: false,
  activeTab: 'lineas',
  editingLineId: null,
  showAddLineForm: false,

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusFilter: (s) => set({ statusFilter: s }),
  setCustomerFilter: (id) => set({ customerFilter: id }),
  setShowAllVersions: (v) => set({ showAllVersions: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setEditingLineId: (id) => set({ editingLineId: id }),
  setShowAddLineForm: (show) => set({ showAddLineForm: show }),
}))
