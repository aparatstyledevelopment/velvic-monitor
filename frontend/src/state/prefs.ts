import { create } from "zustand";

export type Theme = "light" | "dark";
export type InterfaceSize = "small" | "medium" | "large";

export interface PrefsState {
  theme: Theme;
  interfaceSize: InterfaceSize;
  /**
   * Demo-only escape hatch. When true, the chat orchestrator's on/off-topic
   * guardrail is skipped for every turn the user sends in this browser.
   * Intended for live product demos; not exposed by default for tenants.
   */
  disableTopicGate: boolean;
  setTheme: (t: Theme) => void;
  setInterfaceSize: (s: InterfaceSize) => void;
  setDisableTopicGate: (b: boolean) => void;
}

interface Persisted {
  theme: Theme;
  interfaceSize: InterfaceSize;
  disableTopicGate: boolean;
}

const STORAGE_KEY = "prefs";

const DEFAULTS: Persisted = {
  theme: "light",
  interfaceSize: "medium",
  disableTopicGate: false,
};

function readInitial(): Persisted {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<Persisted>;
    return {
      theme: parsed.theme ?? DEFAULTS.theme,
      interfaceSize: parsed.interfaceSize ?? DEFAULTS.interfaceSize,
      disableTopicGate: parsed.disableTopicGate ?? DEFAULTS.disableTopicGate,
    };
  } catch {
    return DEFAULTS;
  }
}

function persist(state: Persisted): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  // theme + size both flow through data-* attributes so tokens.css can
  // override --ui-scale and --surface-* variables in one place.
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.dataset.size = state.interfaceSize;
}

const initial = readInitial();
if (typeof document !== "undefined") {
  // Make sure the saved preferences are reflected on first paint, before
  // any component reads tokenised CSS variables. Without this the very
  // first render uses default-medium scale even when the user picked
  // small/large in a previous session.
  document.documentElement.dataset.theme = initial.theme;
  document.documentElement.dataset.size = initial.interfaceSize;
}

export const usePrefs = create<PrefsState>((set, get) => ({
  ...initial,
  setTheme: (theme) => {
    set({ theme });
    persist({ ...snapshot(get()), theme });
  },
  setInterfaceSize: (interfaceSize) => {
    set({ interfaceSize });
    persist({ ...snapshot(get()), interfaceSize });
  },
  setDisableTopicGate: (disableTopicGate) => {
    set({ disableTopicGate });
    persist({ ...snapshot(get()), disableTopicGate });
  },
}));

function snapshot(state: PrefsState): Persisted {
  return {
    theme: state.theme,
    interfaceSize: state.interfaceSize,
    disableTopicGate: state.disableTopicGate,
  };
}
