import { api } from "./client";
import type { components } from "@shared/openapi/types";

export type LLMUsageSummary = components["schemas"]["LLMUsageSummary"];
export type LLMSurfaceUsage = components["schemas"]["LLMSurfaceUsage"];
export type LLMModelUsage = components["schemas"]["LLMModelUsage"];

export const llmUsageApi = {
  summary: () => api<LLMUsageSummary>("/llm/usage/summary"),
};
