import { create } from 'zustand'
import type { InvoiceEffectiveStatus } from '../types'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface InvoiceUIState {
  searchQuery: string
  statusFilter: InvoiceEffectiveStatus | null
  customerFilter: string | null
  workOrderFilter: string | null
  overdueOnly: boolean
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: InvoiceEffectiveStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setWorkOrderFilter: (id: string | null) => void
  setOverdueOnly: (v: boolean) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useInvoiceStore = create<InvoiceUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  workOrderFilter: null,
  overdueOnly: false,
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setStatusFilter: (s) => set({ statusFilter: s, page: 1 }),
  setCustomerFilter: (id) => set({ customerFilter: id, page: 1 }),
  setWorkOrderFilter: (id) => set({ workOrderFilter: id, page: 1 }),
  setOverdueOnly: (v) => set({ overdueOnly: v, page: 1 }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
