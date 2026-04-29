/**
 * Thin fetch wrapper. All requests are same-origin via Vite's dev proxy
 * (or same-origin in prod), so cookies flow automatically. Errors normalize
 * onto a single shape.
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
    throw new ApiError(resp.status, code, message);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
