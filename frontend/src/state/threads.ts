import { create } from "zustand";

interface ThreadsState {
  activeThreadId: string | null;
  setActiveThreadId: (id: string | null) => void;
}

export const useThreads = create<ThreadsState>((set) => ({
  activeThreadId: null,
  setActiveThreadId: (id) => set({ activeThreadId: id }),
}));
