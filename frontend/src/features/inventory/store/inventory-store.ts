import { create } from 'zustand'

type ActiveTab = 'ficha' | 'stock' | 'proveedores' | 'movimientos'

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface InventoryUIState {
  searchQuery: string
  supplierFilter: string | null
  lowStockOnly: boolean
  activeTab: ActiveTab
  page: number
  pageSize: PageSize

  setSearchQuery: (q: string) => void
  setSupplierFilter: (id: string | null) => void
  setLowStockOnly: (v: boolean) => void
  setActiveTab: (tab: ActiveTab) => void
  setPage: (page: number) => void
  setPageSize: (size: PageSize) => void
}

export const useInventoryStore = create<InventoryUIState>((set) => ({
  searchQuery: '',
  supplierFilter: null,
  lowStockOnly: false,
  activeTab: 'ficha',
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setSupplierFilter: (id) => set({ supplierFilter: id, page: 1 }),
  setLowStockOnly: (v) => set({ lowStockOnly: v, page: 1 }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}))
