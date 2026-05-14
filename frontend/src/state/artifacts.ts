import { create } from "zustand";
import type { components } from "@shared/openapi/types";

import { engineCallsApi } from "../api/engineCalls";

export type EngineCallEnvelope = components["schemas"]["EngineCallOut"];

/** A populated engine call — happy path. */
export interface EngineCallEntry {
  kind: "engine_call";
  engine_call_id: string;
  envelope: EngineCallEnvelope | null; // null while loading
  error: string | null;
  expanded: boolean;
}

/** A placeholder for a number the model emitted without a citation. */
export interface UncitedEntry {
  kind: "uncited";
  key: string; // unique within the entries array
  value: string; // the raw number-shaped fragment, e.g. "2.1%"
  expanded: boolean;
}

export type ArtifactEntry = EngineCallEntry | UncitedEntry;

/**
 * Two view modes:
 *
 * - `single` — one expanded item. Used when the user clicks a citation
 *   chip (cited number) or a red uncited chip.
 * - `list`   — N collapsed rows (one per cited engine_call_id), click
 *   to expand each. Used by the response card's Sources button.
 */
interface ArtifactsState {
  entries: ArtifactEntry[];
  viewMode: "single" | "list";
  paneOpenMobile: boolean;
  openSingle: (engineCallId: string) => Promise<void>;
  openUncited: (value: string) => void;
  openList: (engineCallIds: readonly string[]) => Promise<void>;
  toggleExpanded: (key: string) => void;
  clear: () => void;
  openPaneMobile: () => void;
  closePaneMobile: () => void;
}

function keyOf(entry: ArtifactEntry): string {
  return entry.kind === "engine_call" ? entry.engine_call_id : entry.key;
}

export const useArtifacts = create<ArtifactsState>((set, get) => ({
  entries: [],
  viewMode: "single",
  paneOpenMobile: false,

  openSingle: async (engineCallId) => {
    const current = get().entries[0];
    if (
      get().viewMode === "single" &&
      current?.kind === "engine_call" &&
      current.engine_call_id === engineCallId &&
      current.envelope !== null
    ) {
      return;
    }
    set({
      viewMode: "single",
      entries: [
        {
          kind: "engine_call",
          engine_call_id: engineCallId,
          envelope: null,
          error: null,
          expanded: true,
        },
      ],
    });
    try {
      const envelope = await engineCallsApi.get(engineCallId);
      set((s) => ({
        entries: s.entries.map((e) =>
          e.kind === "engine_call" && e.engine_call_id === engineCallId
            ? { ...e, envelope, error: null }
            : e,
        ),
      }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load source";
      set((s) => ({
        entries: s.entries.map((e) =>
          e.kind === "engine_call" && e.engine_call_id === engineCallId
            ? { ...e, error: message }
            : e,
        ),
      }));
    }
  },

  openUncited: (value) =>
    set({
      viewMode: "single",
      entries: [
        {
          kind: "uncited",
          key: `uncited:${value}:${Date.now()}`,
          value,
          expanded: true,
        },
      ],
    }),

  openList: async (engineCallIds) => {
    const ids = Array.from(new Set(engineCallIds)).filter((id) => id.length > 0);
    if (ids.length === 0) return;
    set({
      viewMode: "list",
      entries: ids.map((id) => ({
        kind: "engine_call" as const,
        engine_call_id: id,
        envelope: null,
        error: null,
        expanded: false,
      })),
    });
    await Promise.all(
      ids.map(async (id) => {
        try {
          const envelope = await engineCallsApi.get(id);
          set((s) => ({
            entries: s.entries.map((e) =>
              e.kind === "engine_call" && e.engine_call_id === id
                ? { ...e, envelope, error: null }
                : e,
            ),
          }));
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to load source";
          set((s) => ({
            entries: s.entries.map((e) =>
              e.kind === "engine_call" && e.engine_call_id === id
                ? { ...e, error: message }
                : e,
            ),
          }));
        }
      }),
    );
  },

  toggleExpanded: (key) =>
    set((s) => ({
      entries: s.entries.map((e) =>
        keyOf(e) === key ? { ...e, expanded: !e.expanded } : e,
      ),
    })),

  clear: () =>
    set({ entries: [], viewMode: "single", paneOpenMobile: false }),
  openPaneMobile: () => set({ paneOpenMobile: true }),
  closePaneMobile: () => set({ paneOpenMobile: false }),
}));
