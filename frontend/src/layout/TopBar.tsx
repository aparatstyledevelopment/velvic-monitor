import { useQuery } from "@tanstack/react-query";
import { Bell, Search } from "lucide-react";

import { driversApi, type CompanySnapshot } from "../api/drivers";
import { engineCallsApi } from "../api/engineCalls";
import { IconButton } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { useCompanies } from "../state/companies";

const FALLBACK = { name: "—", ticker: "—", market: "—" } as const;

function formatPrice(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return p.toLocaleString("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatReturn(r: number | null | undefined): {
  text: string;
  tone: "positive" | "negative" | "neutral";
} {
  if (r === null || r === undefined) return { text: "—", tone: "neutral" };
  const sign = r >= 0 ? "▲" : "▼";
  const tone = r >= 0 ? "positive" : "negative";
  const formatted = Math.abs(r).toLocaleString("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return { text: `${sign} ${formatted}%`, tone };
}

export function TopBar() {
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);

  const { data } = useQuery<CompanySnapshot | null>({
    queryKey: ["snapshot", activeCompanyId],
    queryFn: () =>
      activeCompanyId === null
        ? Promise.resolve(null)
        : driversApi.snapshot(activeCompanyId),
    enabled: activeCompanyId !== null,
  });

  const ticker = data?.ticker ?? FALLBACK.ticker;
  const name = data?.name ?? FALLBACK.name;
  const market = data?.market ?? FALLBACK.market;
  const price = formatPrice(data?.price);
  const ret = formatReturn(data?.return_pct);
  const priceCallId = data?.price_engine_call_id ?? null;

  const push = useArtifacts((s) => s.push);
  const openPaneMobile = useArtifacts((s) => s.openPaneMobile);

  async function openPriceSource() {
    if (priceCallId === null) return;
    const envelope = await engineCallsApi.get(priceCallId);
    push(envelope);
    openPaneMobile();
  }

  const toneClass =
    ret.tone === "positive"
      ? "text-signal-positive"
      : ret.tone === "negative"
        ? "text-signal-negative"
        : "text-text-tertiary";

  return (
    <header
      className="flex items-center gap-lg px-xl h-14 border-b border-border bg-surface shrink-0"
      aria-label="Company snapshot"
    >
      <div className="flex items-baseline gap-md min-w-0 flex-1">
        <button
          type="button"
          onClick={openPriceSource}
          disabled={priceCallId === null}
          className="t-section font-semibold tracking-tight truncate hover:opacity-80 disabled:cursor-default disabled:hover:opacity-100"
          aria-label={
            priceCallId === null
              ? `${ticker} ticker`
              : `${ticker} ticker — open source`
          }
        >
          {ticker}
        </button>
        <span aria-hidden="true" className="text-text-quaternary">
          ·
        </span>
        <span className="t-numeric text-[15px] truncate">{price} SEK</span>
        <span className={["t-numeric text-[14px] shrink-0", toneClass].join(" ")}>
          {ret.text}
        </span>
        <span aria-hidden="true" className="text-text-quaternary hidden md:inline">
          ·
        </span>
        <span className="t-small text-text-tertiary truncate hidden md:inline">
          {name === FALLBACK.name ? market : market}
        </span>
      </div>

      <div className="hidden md:flex items-center gap-sm">
        <SearchStub />
        <IconButton label="Notifications (coming soon)" disabled>
          <Bell size={16} aria-hidden="true" />
        </IconButton>
      </div>
    </header>
  );
}

function SearchStub() {
  return (
    <div
      role="search"
      aria-disabled="true"
      className="flex items-center gap-sm h-9 w-72 px-md rounded-pill border border-border bg-surface-muted text-text-tertiary cursor-not-allowed"
      title="Global search — coming soon"
    >
      <Search size={14} aria-hidden="true" />
      <span className="t-small truncate">Search owners, contacts, reports…</span>
    </div>
  );
}
