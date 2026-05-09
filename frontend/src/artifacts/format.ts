/**
 * Formatting + tool metadata for the artifact card. Centralises the
 * mapping from raw envelope keys to human labels and the heuristics that
 * pick a renderer (table vs field list vs SQL) based on data shape.
 *
 * No new wire fields: every helper here works against the existing
 * `EngineCallOut` shape (tool_name, params, data, sources).
 */

import type { EngineCallEnvelope } from "../state/artifacts";

export interface ToolMeta {
  title: string;
  category: string;
}

const FALLBACK_META: ToolMeta = { title: "Engine call", category: "Engine" };

const TOOL_META: Record<string, ToolMeta> = {
  get_price_move: { title: "Price action", category: "Pricing" },
  get_benchmark_move: { title: "Benchmark return", category: "Pricing" },
  get_peer_returns: { title: "Peer returns", category: "Pricing" },
  get_sector_proxy_return: { title: "Sector proxy", category: "Pricing" },
  get_macro_snapshot: { title: "Macro snapshot", category: "Macro" },
  get_news_for_company: { title: "Company news", category: "News" },
  get_company_meta: { title: "Company metadata", category: "Reference" },
  get_attribution: { title: "Daily attribution", category: "Attribution" },
  get_press_release_summary: { title: "Press release", category: "News" },
  ad_hoc_query: { title: "Ad-hoc query", category: "SQL" },
};

export function toolMeta(name: string): ToolMeta {
  return TOOL_META[name] ?? { ...FALLBACK_META, title: humaniseKey(name) };
}

export function humaniseKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\bid\b/g, "ID")
    .replace(/\bpct\b/g, "%")
    .replace(/\bsek\b/gi, "SEK")
    .replace(/\busd\b/gi, "USD")
    .replace(/\b([a-z])/, (m) => m.toUpperCase());
}

const PRICE_KEYS = new Set([
  "open",
  "high",
  "low",
  "close",
  "last_close",
  "prior_close",
]);

const PERCENT_SUFFIXES = ["_pct", "_pp", "_return"];

export function formatScalar(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return formatNumber(key, value);
  if (typeof value === "string") {
    if (looksLikeDate(value)) return formatDate(value);
    if (looksLikeNumeric(value)) return formatNumber(key, Number(value));
    return value;
  }
  return JSON.stringify(value);
}

function formatNumber(key: string, value: number): string {
  if (!Number.isFinite(value)) return "—";
  const isPercent = PERCENT_SUFFIXES.some((suf) => key.endsWith(suf));
  if (isPercent) return formatPercent(value);
  if (PRICE_KEYS.has(key)) return formatPrice(value);
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  // generic float — drop trailing zeros, max 4 decimals
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function formatPercent(value: number): string {
  const abs = Math.abs(value);
  // backend returns percentages already (e.g. -0.85 means -0.85%, not -85%).
  // We don't multiply.
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${formatted}%`;
}

export function formatPrice(value: number): string {
  return value.toLocaleString("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}/;

function looksLikeDate(value: string): boolean {
  return ISO_DATE_RE.test(value);
}

function looksLikeNumeric(value: string): boolean {
  if (value.length === 0) return false;
  const n = Number(value);
  return !Number.isNaN(n) && Number.isFinite(n);
}

export function formatDate(value: string): string {
  // Trim time portion if any; keep the YYYY-MM-DD prefix as-is.
  // Display order intentionally preserved (ISO is unambiguous).
  return value.slice(0, 10);
}

export type ResponseShape =
  | { kind: "sql"; sql: string; columns: readonly string[]; rows: readonly unknown[][] }
  | { kind: "records"; key: string | null; columns: readonly string[]; rows: readonly Record<string, unknown>[]; scalars: readonly [string, unknown][] }
  | { kind: "fields"; scalars: readonly [string, unknown][] }
  | { kind: "json"; raw: unknown };

/**
 * Inspect `data` and pick a presentation:
 *
 * - `ad_hoc_query`-shaped: { sql, result: { columns, rows } } → SQL view
 * - flat object containing exactly one array-of-records: split into
 *   "scalars" + "records" (table) so the eye can scan both
 * - flat object of scalars: field list
 * - anything else: pretty JSON fallback
 */
export function inspectResponse(envelope: EngineCallEnvelope): ResponseShape {
  const data = envelope.data;
  if (envelope.tool_name === "ad_hoc_query" && isRecord(data)) {
    const sql = typeof data.sql === "string" ? data.sql : "";
    const result = data.result;
    if (isRecord(result)) {
      const columns = Array.isArray(result.columns)
        ? (result.columns as string[])
        : [];
      const rows = Array.isArray(result.rows)
        ? (result.rows as unknown[][])
        : [];
      return { kind: "sql", sql, columns, rows };
    }
  }

  if (!isRecord(data)) {
    return { kind: "json", raw: data };
  }

  const entries = Object.entries(data);
  const records: { key: string; rows: Record<string, unknown>[] }[] = [];
  const scalars: [string, unknown][] = [];
  for (const [k, v] of entries) {
    if (Array.isArray(v) && v.length > 0 && v.every(isRecord)) {
      records.push({ key: k, rows: v });
    } else {
      scalars.push([k, v]);
    }
  }

  if (records.length === 1 && records[0]) {
    const rec = records[0];
    const columns = unionKeys(rec.rows);
    return {
      kind: "records",
      key: rec.key,
      columns,
      rows: rec.rows,
      scalars,
    };
  }

  if (records.length === 0) {
    return { kind: "fields", scalars };
  }

  // 2+ array-of-records — fall back to JSON for now; the view rarely has
  // both at once and adding multi-table layout is a follow-up.
  return { kind: "json", raw: data };
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function unionKeys(rows: readonly Record<string, unknown>[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (!seen.has(k)) {
        seen.add(k);
        out.push(k);
      }
    }
  }
  return out;
}

/**
 * Render a tool-call literal: `tool_name(arg1 = "value", arg2 = 42)`.
 * Used as a stand-in "query" view for typed engine tools, where the
 * function call itself is the query.
 */
export function renderFunctionCall(
  toolName: string,
  params: Record<string, unknown>,
): string {
  const entries = Object.entries(params);
  if (entries.length === 0) return `${toolName}()`;
  const lines = entries.map(([k, v]) => `  ${k} = ${formatLiteral(v)},`);
  return `${toolName}(\n${lines.join("\n")}\n)`;
}

function formatLiteral(v: unknown): string {
  if (v === null) return "null";
  if (v === undefined) return "undefined";
  if (typeof v === "string") return JSON.stringify(v);
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

/**
 * One-line, deterministic explanation per known tool. Falls back to
 * "tool produced N field(s)" so unknown tools still get a label.
 *
 * No LLM round-trip — these are templates that read off the data
 * directly. Swap to LLM-generated copy in a follow-up if needed.
 */
export function describeArtifact(envelope: EngineCallEnvelope): string | null {
  const d = envelope.data as Record<string, unknown>;
  switch (envelope.tool_name) {
    case "get_price_move": {
      const ticker = stringOf(d.ticker) ?? "—";
      const close = numberOf(d.last_close);
      const ret = numberOf(d.daily_return_pct);
      const date = stringOf(d.last_close_date);
      const closeS = close === null ? "—" : `${formatPrice(close)} SEK`;
      const retS = ret === null ? "" : ` (${formatPercent(ret)})`;
      const dateS = date === null ? "" : ` on ${formatDate(date)}`;
      return `${ticker} closed at ${closeS}${retS}${dateS}.`;
    }
    case "get_benchmark_move": {
      const name = stringOf(d.benchmark) ?? "Benchmark";
      const ret = numberOf(d.daily_return_pct);
      const date = stringOf(d.as_of);
      const retS = ret === null ? "—" : formatPercent(ret);
      const dateS = date === null ? "" : ` on ${formatDate(date)}`;
      return `${name} returned ${retS}${dateS}.`;
    }
    case "get_peer_returns": {
      const peers = Array.isArray(d.peers) ? d.peers : [];
      return `${peers.length} peer${peers.length === 1 ? "" : "s"} compared.`;
    }
    case "get_sector_proxy_return": {
      const ret = numberOf(d.daily_return_pct);
      return ret === null
        ? "Sector proxy return."
        : `Sector proxy returned ${formatPercent(ret)}.`;
    }
    case "get_news_for_company": {
      const items = Array.isArray(d.items) ? d.items : [];
      return `${items.length} news item${items.length === 1 ? "" : "s"} found.`;
    }
    case "get_attribution": {
      const idio = numberOf(d.idiosyncratic_pct);
      return idio === null
        ? "Daily return attribution."
        : `Idiosyncratic component: ${formatPercent(idio)}.`;
    }
    case "get_company_meta": {
      const name = stringOf(d.name) ?? stringOf(d.ticker) ?? "Company";
      const sector = stringOf(d.sector);
      return sector === null ? `${name}.` : `${name} · ${sector}.`;
    }
    case "ad_hoc_query": {
      const result = isRecord(d.result) ? d.result : null;
      const rows = result && Array.isArray(result.rows) ? result.rows.length : 0;
      const truncated = result?.truncated === true;
      return `${rows} row${rows === 1 ? "" : "s"} returned${truncated ? " (truncated)" : ""}.`;
    }
    default:
      return null;
  }
}

function stringOf(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

function numberOf(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}
