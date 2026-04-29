import { create } from "zustand";

export interface Me {
  user_id: string;
  org_id: string;
  email: string;
  display_name: string | null;
  role: string;
  org_name: string;
}

interface AuthState {
  me: Me | null;
  loading: boolean;
  setMe: (m: Me | null) => void;
  setLoading: (b: boolean) => void;
}

export const useAuth = create<AuthState>((set) => ({
  me: null,
  loading: true,
  setMe: (me) => set({ me }),
  setLoading: (loading) => set({ loading }),
}));
