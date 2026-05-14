import { create } from "zustand";

interface ComposerState {
  draft: string;
  setDraft: (text: string) => void;
  clear: () => void;
  /** Append text to the current draft (e.g. when chip insertion adds a follow-up). */
  prefill: (text: string) => void;
}

export const useComposer = create<ComposerState>((set) => ({
  draft: "",
  setDraft: (draft) => set({ draft }),
  clear: () => set({ draft: "" }),
  prefill: (text) => set({ draft: text }),
}));
