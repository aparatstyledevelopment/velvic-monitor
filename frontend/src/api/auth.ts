import { api } from "./client";
import type { Me } from "../state/auth";

export interface SignupBody {
  email: string;
  password: string;
  org_name: string;
  display_name?: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export const authApi = {
  signup: (body: SignupBody) => api<{ user_id: string }>("/auth/signup", { method: "POST", body }),
  login: (body: LoginBody) => api<{ user_id: string }>("/auth/login", { method: "POST", body }),
  logout: () => api<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => api<Me>("/auth/me"),
};
