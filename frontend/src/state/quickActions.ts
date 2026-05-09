import { create } from "zustand";

interface QuickActionsState {
  open: boolean;
  toggle: () => void;
  openPanel: () => void;
  closePanel: () => void;
}

export const useQuickActions = create<QuickActionsState>((set, get) => ({
  open: false,
  toggle: () => set({ open: !get().open }),
  openPanel: () => set({ open: true }),
  closePanel: () => set({ open: false }),
}));
