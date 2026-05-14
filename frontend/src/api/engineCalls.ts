import { api } from "./client";
import type { components } from "@shared/openapi/types";

export type EngineCallOut = components["schemas"]["EngineCallOut"];

export const engineCallsApi = {
  get: (engineCallId: string) => api<EngineCallOut>(`/engine_calls/${engineCallId}`),
};
