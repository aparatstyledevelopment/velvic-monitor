import { api } from "./client";
import type { components } from "@shared/openapi/types";

export type CompanyOut = components["schemas"]["CompanyOut"];

export const companiesApi = {
  list: () => api<CompanyOut[]>("/me/companies"),
};
