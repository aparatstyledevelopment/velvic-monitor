import { api } from "./client";
import type { components } from "@shared/openapi/types";

export type BriefingOut = components["schemas"]["BriefingOut"];
export type EngineCallOut = components["schemas"]["EngineCallOut"];

export const briefingsApi = {
  latest: (companyId: number) =>
    api<BriefingOut>(`/companies/${companyId}/briefings/latest`),
  forDate: (companyId: number, date: string) =>
    api<BriefingOut>(`/companies/${companyId}/briefings/${date}`),
  evidence: (companyId: number, date: string) =>
    api<EngineCallOut[]>(`/companies/${companyId}/briefings/${date}/evidence`),
};
