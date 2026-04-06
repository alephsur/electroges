import { create } from "zustand";

interface SupplierStoreState {
  searchQuery: string;
  isActiveFilter: boolean;

  setSearchQuery: (q: string) => void;
  setIsActiveFilter: (value: boolean) => void;
}

export const useSupplierStore = create<SupplierStoreState>((set) => ({
  searchQuery: "",
  isActiveFilter: true,

  setSearchQuery: (q) => set({ searchQuery: q }),
  setIsActiveFilter: (value) => set({ isActiveFilter: value }),
}));
