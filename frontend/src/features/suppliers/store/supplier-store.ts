import { create } from "zustand";

interface SupplierStoreState {
  searchQuery: string;
  isActiveFilter: boolean;
  selectedSupplierId: string | null;

  setSearchQuery: (q: string) => void;
  setIsActiveFilter: (value: boolean) => void;
  setSelectedSupplierId: (id: string | null) => void;
}

export const useSupplierStore = create<SupplierStoreState>((set) => ({
  searchQuery: "",
  isActiveFilter: true,
  selectedSupplierId: null,

  setSearchQuery: (q) => set({ searchQuery: q }),
  setIsActiveFilter: (value) => set({ isActiveFilter: value }),
  setSelectedSupplierId: (id) => set({ selectedSupplierId: id }),
}));
