import { create } from 'zustand'
import type { SiteVisitStatus } from '../types'

type ActiveTab = 'info' | 'materiales' | 'fotos' | 'documentos'

interface SiteVisitUIState {
  searchQuery: string
  statusFilter: SiteVisitStatus | null
  customerFilter: string | null
  dateRange: { from: string | null; to: string | null }
  selectedVisitId: string | null
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: SiteVisitStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setDateRange: (range: { from: string | null; to: string | null }) => void
  setSelectedVisitId: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useSiteVisitStore = create<SiteVisitUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  dateRange: { from: null, to: null },
  selectedVisitId: null,
  activeTab: 'info',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusFilter: (s) => set({ statusFilter: s }),
  setCustomerFilter: (id) => set({ customerFilter: id }),
  setDateRange: (range) => set({ dateRange: range }),
  setSelectedVisitId: (id) => set({ selectedVisitId: id, activeTab: 'info' }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
