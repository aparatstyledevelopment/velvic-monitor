import { create } from "zustand";
import type { components } from "@shared/openapi/types";

import { engineCallsApi } from "../api/engineCalls";

export type EngineCallEnvelope = components["schemas"]["EngineCallOut"];

interface ArtifactsState {
  /** Single active artifact at a time — clicking a citation replaces. */
  stack: EngineCallEnvelope[];
  loadingIds: ReadonlySet<string>;
  paneOpenMobile: boolean;
  push: (envelope: EngineCallEnvelope) => void;
  loadById: (engineCallId: string) => Promise<void>;
  clear: () => void;
  openPaneMobile: () => void;
  closePaneMobile: () => void;
}

export const useArtifacts = create<ArtifactsState>((set, get) => ({
  stack: [],
  loadingIds: new Set<string>(),
  paneOpenMobile: false,
  push: (envelope) => set({ stack: [envelope] }),
  loadById: async (engineCallId) => {
    const { stack, loadingIds } = get();
    if (stack[0]?.engine_call_id === engineCallId) return;
    if (loadingIds.has(engineCallId)) return;
    const next = new Set(loadingIds);
    next.add(engineCallId);
    set({ loadingIds: next, stack: [] });
    try {
      const envelope = await engineCallsApi.get(engineCallId);
      set((s) => {
        const remaining = new Set(s.loadingIds);
        remaining.delete(engineCallId);
        return { loadingIds: remaining, stack: [envelope] };
      });
    } catch (err) {
      set((s) => {
        const remaining = new Set(s.loadingIds);
        remaining.delete(engineCallId);
        return { loadingIds: remaining };
      });
      throw err;
    }
  },
  clear: () => set({ stack: [], loadingIds: new Set<string>() }),
  openPaneMobile: () => set({ paneOpenMobile: true }),
  closePaneMobile: () => set({ paneOpenMobile: false }),
}));
