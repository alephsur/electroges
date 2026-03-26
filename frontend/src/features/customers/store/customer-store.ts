import { create } from 'zustand'
import type { CustomerType } from '../types'

type ActiveTab = 'timeline' | 'ficha' | 'direcciones' | 'documentos'

interface CustomerUIState {
  searchQuery: string
  typeFilter: CustomerType | null
  showInactive: boolean
  selectedCustomerId: string | null
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setTypeFilter: (t: CustomerType | null) => void
  setShowInactive: (v: boolean) => void
  setSelectedCustomerId: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useCustomerStore = create<CustomerUIState>((set) => ({
  searchQuery: '',
  typeFilter: null,
  showInactive: false,
  selectedCustomerId: null,
  activeTab: 'timeline',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setTypeFilter: (t) => set({ typeFilter: t }),
  setShowInactive: (v) => set({ showInactive: v }),
  setSelectedCustomerId: (id) => set({ selectedCustomerId: id, activeTab: 'timeline' }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
