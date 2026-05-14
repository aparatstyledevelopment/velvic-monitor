import type { components } from "../../../shared/openapi/types";

import { api } from "./client";

export type CompanySnapshot = components["schemas"]["CompanySnapshotOut"];
export type DriversData = components["schemas"]["DriversDataOut"];

export const driversApi = {
  snapshot: (companyId: number) =>
    api<CompanySnapshot>(`/companies/${companyId}/snapshot`),
  data: (companyId: number, source: string) =>
    api<DriversData>(`/companies/${companyId}/drivers/data/${source}`),
};

export const DRIVERS_DATA_SOURCES = [
  {
    key: "price_action",
    label: "Price action",
    description: "Today's price, return, and reference levels.",
  },
  {
    key: "comparators",
    label: "Comparators",
    description: "Benchmark, sector proxy, and peer returns.",
  },
  {
    key: "news_flow",
    label: "News flow",
    description: "Regulatory and IR news in the last five days.",
  },
  {
    key: "macro",
    label: "Macro context",
    description: "Today's FX, rate, and central-bank macro snapshot.",
  },
  {
    key: "attribution",
    label: "Daily attribution",
    description: "Computed return decomposition vs benchmark and sector.",
  },
] as const;

export type DriversDataSourceKey = (typeof DRIVERS_DATA_SOURCES)[number]["key"];
