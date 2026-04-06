import { create } from 'zustand'
import type { InvoiceEffectiveStatus } from '../types'

interface InvoiceUIState {
  searchQuery: string
  statusFilter: InvoiceEffectiveStatus | null
  customerFilter: string | null
  workOrderFilter: string | null
  overdueOnly: boolean

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: InvoiceEffectiveStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setWorkOrderFilter: (id: string | null) => void
  setOverdueOnly: (v: boolean) => void
}

export const useInvoiceStore = create<InvoiceUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  workOrderFilter: null,
  overdueOnly: false,

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusFilter: (s) => set({ statusFilter: s }),
  setCustomerFilter: (id) => set({ customerFilter: id }),
  setWorkOrderFilter: (id) => set({ workOrderFilter: id }),
  setOverdueOnly: (v) => set({ overdueOnly: v }),
}))
