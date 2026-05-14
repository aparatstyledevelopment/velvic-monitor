/**
 * Thin fetch wrapper. All requests are same-origin via Vite's dev proxy
 * (or same-origin in prod), so cookies flow automatically. Errors normalize
 * onto a single shape.
 *
 * On any 401 response we dispatch a single `auth:unauthorized` event so
 * higher-level state (auth store + router) can react once instead of
 * letting individual queries pile up "401 (Unauthorized)" rows in the
 * console. This is the in-flight equivalent of the boot-time `/auth/me`
 * check — needed because cookies expire mid-session.
 */

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

let lastUnauthorizedAt = 0;

function notifyUnauthorized(): void {
  if (typeof window === "undefined") return;
  const now = Date.now();
  if (now - lastUnauthorizedAt < 1_000) return;
  lastUnauthorizedAt = now;
  window.dispatchEvent(new CustomEvent("auth:unauthorized"));
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const init: RequestInit = {
    method: opts.method ?? "GET",
    credentials: "include",
    headers: { "content-type": "application/json" },
  };
  if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
  }
  if (opts.signal) init.signal = opts.signal;

  const resp = await fetch(`/api${path}`, init);
  if (!resp.ok) {
    let code = "http_error";
    let message = resp.statusText;
    try {
      const detail = (await resp.json()) as { code?: string; message?: string };
      code = detail.code ?? code;
      message = detail.message ?? message;
    } catch {
      /* ignore — non-JSON error body */
    }
    if (resp.status === 401 && path !== "/auth/me") {
      notifyUnauthorized();
    }
    throw new ApiError(resp.status, code, message);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
