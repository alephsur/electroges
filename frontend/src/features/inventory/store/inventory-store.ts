import { create } from 'zustand'

type ActiveTab = 'ficha' | 'stock' | 'proveedores' | 'movimientos'

interface InventoryUIState {
  searchQuery: string
  supplierFilter: string | null
  lowStockOnly: boolean
  selectedItemId: string | null
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setSupplierFilter: (id: string | null) => void
  setLowStockOnly: (v: boolean) => void
  setSelectedItemId: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useInventoryStore = create<InventoryUIState>((set) => ({
  searchQuery: '',
  supplierFilter: null,
  lowStockOnly: false,
  selectedItemId: null,
  activeTab: 'ficha',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setSupplierFilter: (id) => set({ supplierFilter: id }),
  setLowStockOnly: (v) => set({ lowStockOnly: v }),
  setSelectedItemId: (id) => set({ selectedItemId: id, activeTab: 'ficha' }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
