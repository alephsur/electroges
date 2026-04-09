import { create } from 'zustand'
import type { CustomerType } from '../types'

type ActiveTab = 'timeline' | 'ficha' | 'direcciones' | 'documentos'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface CustomerUIState {
  searchQuery: string
  typeFilter: CustomerType | null
  showInactive: boolean
  activeTab: ActiveTab
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setTypeFilter: (t: CustomerType | null) => void
  setShowInactive: (v: boolean) => void
  setActiveTab: (tab: ActiveTab) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useCustomerStore = create<CustomerUIState>((set) => ({
  searchQuery: '',
  typeFilter: null,
  showInactive: false,
  activeTab: 'timeline',
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setTypeFilter: (t) => set({ typeFilter: t, page: 1 }),
  setShowInactive: (v) => set({ showInactive: v, page: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
