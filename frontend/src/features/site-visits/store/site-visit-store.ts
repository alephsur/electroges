import { create } from 'zustand'
import type { SiteVisitStatus } from '../types'

type ActiveTab = 'info' | 'materiales' | 'fotos' | 'documentos'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface SiteVisitUIState {
  searchQuery: string
  statusFilter: SiteVisitStatus | null
  customerFilter: string | null
  dateRange: { from: string | null; to: string | null }
  activeTab: ActiveTab
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: SiteVisitStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setDateRange: (range: { from: string | null; to: string | null }) => void
  setActiveTab: (tab: ActiveTab) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useSiteVisitStore = create<SiteVisitUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  dateRange: { from: null, to: null },
  activeTab: 'info',
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setStatusFilter: (s) => set({ statusFilter: s, page: 1 }),
  setCustomerFilter: (id) => set({ customerFilter: id, page: 1 }),
  setDateRange: (range) => set({ dateRange: range, page: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
