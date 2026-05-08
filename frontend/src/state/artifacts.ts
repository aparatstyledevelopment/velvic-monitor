import { create } from "zustand";
import type { components } from "@shared/openapi/types";

export type EngineCallEnvelope = components["schemas"]["EngineCallOut"];

interface ArtifactsState {
  stack: EngineCallEnvelope[];
  paneOpenMobile: boolean;
  push: (envelope: EngineCallEnvelope) => void;
  clear: () => void;
  openPaneMobile: () => void;
  closePaneMobile: () => void;
}

export const useArtifacts = create<ArtifactsState>((set) => ({
  stack: [],
  paneOpenMobile: false,
  push: (envelope) =>
    set((state) => {
      if (state.stack.some((e) => e.engine_call_id === envelope.engine_call_id)) {
        return state;
      }
      return { stack: [envelope, ...state.stack] };
    }),
  clear: () => set({ stack: [] }),
  openPaneMobile: () => set({ paneOpenMobile: true }),
  closePaneMobile: () => set({ paneOpenMobile: false }),
}));
