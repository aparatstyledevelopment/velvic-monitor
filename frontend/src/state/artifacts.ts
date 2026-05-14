import { create } from "zustand";
import type { components } from "@shared/openapi/types";

import { engineCallsApi } from "../api/engineCalls";

export type EngineCallEnvelope = components["schemas"]["EngineCallOut"];

interface ArtifactsState {
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
  push: (envelope) =>
    set((state) => {
      if (state.stack.some((e) => e.engine_call_id === envelope.engine_call_id)) {
        return state;
      }
      return { stack: [envelope, ...state.stack] };
    }),
  loadById: async (engineCallId) => {
    const { stack, loadingIds } = get();
    if (stack.some((e) => e.engine_call_id === engineCallId)) return;
    if (loadingIds.has(engineCallId)) return;
    const next = new Set(loadingIds);
    next.add(engineCallId);
    set({ loadingIds: next });
    try {
      const envelope = await engineCallsApi.get(engineCallId);
      set((s) => {
        const remaining = new Set(s.loadingIds);
        remaining.delete(engineCallId);
        const exists = s.stack.some((e) => e.engine_call_id === envelope.engine_call_id);
        return {
          loadingIds: remaining,
          stack: exists ? s.stack : [envelope, ...s.stack],
        };
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
