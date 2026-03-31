import { create } from 'zustand'
import type { WorkOrderStatus } from '../types'

type ActiveTab = 'resumen' | 'tareas' | 'materiales' | 'pedidos' | 'certificaciones' | 'albaranes' | 'notas'

interface WorkOrderUIState {
  searchQuery: string
  statusFilter: WorkOrderStatus | null
  customerFilter: string | null
  selectedWorkOrderId: string | null
  activeTab: ActiveTab

  setSearchQuery: (q: string) => void
  setStatusFilter: (s: WorkOrderStatus | null) => void
  setCustomerFilter: (id: string | null) => void
  setSelectedWorkOrderId: (id: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
}

export const useWorkOrderStore = create<WorkOrderUIState>((set) => ({
  searchQuery: '',
  statusFilter: null,
  customerFilter: null,
  selectedWorkOrderId: null,
  activeTab: 'resumen',

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusFilter: (s) => set({ statusFilter: s }),
  setCustomerFilter: (id) => set({ customerFilter: id }),
  setSelectedWorkOrderId: (id) =>
    set({ selectedWorkOrderId: id, activeTab: 'resumen' }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
