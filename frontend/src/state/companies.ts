import { create } from "zustand";

interface CompaniesState {
  activeCompanyId: number | null;
  setActiveCompanyId: (id: number | null) => void;
}

export const useCompanies = create<CompaniesState>((set) => ({
  activeCompanyId: null,
  setActiveCompanyId: (id) => set({ activeCompanyId: id }),
}));
