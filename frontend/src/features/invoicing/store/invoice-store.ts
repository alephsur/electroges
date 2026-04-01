import { create } from 'zustand'
import type { InvoiceEffectiveStatus } from '../types'

type ActiveTab = 'lines' | 'payments' | 'notes'

interface InvoiceUIState {
  searchQuery: string
  statusFilter: InvoiceEffectiveStatus | null
  customerFilter: string | null
  workOrderFilter: string | null
  overdueOnly: boolean
  selectedInvoiceId: string | null
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: InvoiceEffectiveStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setWorkOrderFilter: (id: string | null) => void
  setOverdueOnly: (v: boolean) => void
  setSelectedInvoiceId: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useInvoiceStore = create<InvoiceUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  workOrderFilter: null,
  overdueOnly: false,
  selectedInvoiceId: null,
  activeTab: 'lines',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusFilter: (s) => set({ statusFilter: s }),
  setCustomerFilter: (id) => set({ customerFilter: id }),
  setWorkOrderFilter: (id) => set({ workOrderFilter: id }),
  setOverdueOnly: (v) => set({ overdueOnly: v }),
  setSelectedInvoiceId: (id) =>
    set({ selectedInvoiceId: id, activeTab: 'lines' }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
