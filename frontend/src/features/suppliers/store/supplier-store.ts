import { create } from "zustand";

export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number];

interface SupplierStoreState {
  searchQuery: string;
  isActiveFilter: boolean;
  page: number;
  pageSize: PageSize;

  setSearchQuery: (q: string) => void;
  setIsActiveFilter: (value: boolean) => void;
  setPage: (page: number) => void;
  setPageSize: (size: PageSize) => void;
}

export const useSupplierStore = create<SupplierStoreState>((set) => ({
  searchQuery: "",
  isActiveFilter: true,
  page: 1,
  pageSize: 25,

  setSearchQuery: (q) => set({ searchQuery: q, page: 1 }),
  setIsActiveFilter: (value) => set({ isActiveFilter: value, page: 1 }),
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),
}));
