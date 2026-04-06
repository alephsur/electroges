import { create } from 'zustand'

type ActiveTab = 'ficha' | 'stock' | 'proveedores' | 'movimientos'

interface InventoryUIState {
  searchQuery: string
  supplierFilter: string | null
  lowStockOnly: boolean
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setSupplierFilter: (id: string | null) => void
  setLowStockOnly: (v: boolean) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useInventoryStore = create<InventoryUIState>((set) => ({
  searchQuery: '',
  supplierFilter: null,
  lowStockOnly: false,
  activeTab: 'ficha',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setSupplierFilter: (id) => set({ supplierFilter: id }),
  setLowStockOnly: (v) => set({ lowStockOnly: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
