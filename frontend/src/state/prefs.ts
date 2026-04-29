import { create } from "zustand";

export type Theme = "light" | "dark";
export type InterfaceSize = "small" | "medium" | "large";

export interface PrefsState {
  theme: Theme;
  interfaceSize: InterfaceSize;
  setTheme: (t: Theme) => void;
  setInterfaceSize: (s: InterfaceSize) => void;
}

const STORAGE_KEY = "prefs";

function readInitial(): { theme: Theme; interfaceSize: InterfaceSize } {
  if (typeof window === "undefined") return { theme: "light", interfaceSize: "medium" };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { theme: "light", interfaceSize: "medium" };
    const parsed = JSON.parse(raw) as Partial<{ theme: Theme; interfaceSize: InterfaceSize }>;
    return {
      theme: parsed.theme ?? "light",
      interfaceSize: parsed.interfaceSize ?? "medium",
    };
  } catch {
    return { theme: "light", interfaceSize: "medium" };
  }
}

function persist(state: { theme: Theme; interfaceSize: InterfaceSize }): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  document.documentElement.dataset.theme = state.theme;
  const fontSize = { small: "14px", medium: "15px", large: "17px" }[state.interfaceSize];
  document.documentElement.style.fontSize = fontSize;
}

const initial = readInitial();

export const usePrefs = create<PrefsState>((set, get) => ({
  ...initial,
  setTheme: (theme) => {
    set({ theme });
    persist({ ...get(), theme });
  },
  setInterfaceSize: (interfaceSize) => {
    set({ interfaceSize });
    persist({ ...get(), interfaceSize });
  },
}));
