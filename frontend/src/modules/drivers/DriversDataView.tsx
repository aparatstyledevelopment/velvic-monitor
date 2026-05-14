import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../../api/client";
import { driversApi, DRIVERS_DATA_SOURCES } from "../../api/drivers";
import {
  Hairline,
  PillButton,
  Sparkline,
  Stat,
} from "../../design/primitives";
import { TakeoverHeader } from "../../layout/TakeoverHeader";
import { useArtifacts } from "../../state/artifacts";
import { useCompanies } from "../../state/companies";

export function DriversDataView() {
  const { source } = useParams<{ source: string }>();
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);

  const definition = useMemo(
    () => DRIVERS_DATA_SOURCES.find((s) => s.key === source) ?? null,
    [source],
  );

  const dataQ = useQuery({
    queryKey: ["drivers-data", activeCompanyId, source],
    queryFn: () =>
      activeCompanyId === null || source === undefined
        ? Promise.resolve(null)
        : driversApi.data(activeCompanyId, source),
    enabled: activeCompanyId !== null && source !== undefined,
  });

  const openSingle = useArtifacts((s) => s.openSingle);
  const openMobile = useArtifacts((s) => s.openPaneMobile);

  async function openSource(engineCallId: string) {
    openMobile();
    await openSingle(engineCallId);
  }

  if (definition === null) {
    return (
      <div className="px-xl py-2xl max-w-reading mx-auto">
        <TakeoverHeader title="Unknown source" subtitle="No such Drivers data view." />
      </div>
    );
  }

  const data = dataQ.data;

  return (
    <div className="flex flex-col">
      <TakeoverHeader title={definition.label} subtitle={definition.description} />
      <div className="px-xl pb-3xl max-w-reading mx-auto w-full flex flex-col gap-lg">
        {activeCompanyId === null && (
          <EmptyState
            title="Pick a company"
            body="Use the sidebar's company switcher to choose a name in scope, then come back here."
          />
        )}
        {dataQ.isLoading && (
          <p className="t-small text-text-tertiary">Loading data&hellip;</p>
        )}
        {dataQ.error !== null && dataQ.error !== undefined && (
          <DataErrorState error={dataQ.error} />
        )}
        {data !== null && data !== undefined && (
          <>
            <div className="flex items-center gap-sm flex-wrap">
              <span className="t-meta">As of {data.as_of_date}</span>
              {data.engine_call_ids.map((id) => (
                <PillButton key={id} tone="inverse" onClick={() => openSource(id)}>
                  Source · {id.slice(0, 10)}
                </PillButton>
              ))}
            </div>
            <Hairline />
            <SourceView source={definition.key} data={data.data} />
          </>
        )}
      </div>
    </div>
  );
}

function DataErrorState({ error }: { error: unknown }) {
  if (error instanceof ApiError) {
    if (error.code === "no_briefing" || error.status === 404) {
      return (
        <EmptyState
          title="No briefing yet"
          body="The Drivers data view reads from the latest briefing's fact pack. Run `python -m app.admin.backfill` so the pipeline produces a briefing for this company, then refresh."
        />
      );
    }
    return (
      <EmptyState
        title={`Couldn't load (${error.status})`}
        body={error.message}
      />
    );
  }
  return (
    <EmptyState
      title="Couldn't load data"
      body="Try refreshing the page. If this keeps happening, check the backend logs."
    />
  );
}

interface Bag {
  [key: string]: unknown;
}

function SourceView({
  source,
  data,
}: {
  source: string;
  data: Record<string, unknown>;
}) {
  switch (source) {
    case "price_action":
      return <PriceActionView block={pick(data, "price_move")} />;
    case "comparators":
      return (
        <ComparatorsView
          benchmark={pick(data, "benchmark")}
          sector={pick(data, "sector_proxy")}
          peers={pick(data, "peer_returns")}
        />
      );
    case "news_flow":
      return <NewsFlowView block={pick(data, "news")} />;
    case "macro":
      return <MacroView block={pick(data, "macro_snapshot")} />;
    case "attribution":
      return <AttributionView block={pick(data, "attribution")} />;
    default:
      return <pre className="t-mono text-sm">{JSON.stringify(data, null, 2)}</pre>;
  }
}

/* -------------------------------------------------------------- price_action */

function PriceActionView({ block }: { block: Bag | null }) {
  if (block === null) return <EmptyState label="No price data" />;
  const close = num(block.last_close);
  const prior = num(block.prior_close);
  const ret = num(block.daily_return_pct);
  const history = arr(block.five_day_history);
  const series = history
    .map((h) => num((h as Bag).close))
    .filter((v): v is number => v !== null);
  return (
    <div className="flex flex-col gap-lg">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-md">
        <Stat
          label="Last close"
          value={formatPrice(close)}
          meta={`on ${str(block.last_close_date)}`}
        />
        <Stat
          label="Prior close"
          value={formatPrice(prior)}
          meta={`on ${str(block.prior_close_date)}`}
        />
        <Stat
          label="Daily return"
          value={formatReturnPct(ret)}
          tone={returnTone(ret)}
        />
      </div>
      {series.length >= 2 && (
        <figure
          className="flex flex-col gap-xs rounded-lg border border-border bg-surface px-lg py-md"
          aria-label="Five-day close trend"
        >
          <figcaption className="t-meta">Five-day close trend</figcaption>
          <Sparkline
            values={series}
            width={640}
            height={96}
            ariaLabel="Five-day close sparkline"
            className="w-full h-auto"
          />
        </figure>
      )}
      <Table
        title="History"
        head={["Date", "Open", "High", "Low", "Close", "Volume"]}
        rows={history.map((h) => {
          const b = h as Bag;
          return [
            str(b.trading_date),
            formatPrice(num(b.open)),
            formatPrice(num(b.high)),
            formatPrice(num(b.low)),
            formatPrice(num(b.close)),
            formatInt(num(b.volume)),
          ];
        })}
      />
    </div>
  );
}

/* -------------------------------------------------------------- comparators */

function ComparatorsView({
  benchmark,
  sector,
  peers,
}: {
  benchmark: Bag | null;
  sector: Bag | null;
  peers: Bag | null;
}) {
  const benchmarkRet = num(benchmark?.daily_return_pct);
  const sectorRet = num(sector?.daily_return_pct);
  const peerRows = arr(peers?.peers);
  return (
    <div className="flex flex-col gap-lg">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-md">
        <Stat
          label={`Benchmark · ${str(benchmark?.benchmark) || "—"}`}
          value={formatReturnPct(benchmarkRet)}
          tone={returnTone(benchmarkRet)}
          meta={`on ${str(benchmark?.as_of)}`}
        />
        <Stat
          label={`Sector · ${str(sector?.sector) || "—"}`}
          value={formatReturnPct(sectorRet)}
          tone={returnTone(sectorRet)}
          meta={`proxy: ${str(sector?.proxy) || "—"}`}
        />
      </div>
      <Table
        title={`Peers · ${peerRows.length}`}
        head={["Ticker", "Name", "Daily return"]}
        rows={peerRows.map((p) => {
          const b = p as Bag;
          const r = num(b.daily_return_pct);
          return [
            str(b.ticker),
            str(b.name),
            { value: formatReturnPct(r), tone: returnTone(r) },
          ];
        })}
      />
    </div>
  );
}

/* -------------------------------------------------------------- news_flow */

function NewsFlowView({ block }: { block: Bag | null }) {
  if (block === null) return <EmptyState label="No news data" />;
  const items = arr(block.items);
  if (items.length === 0)
    return (
      <EmptyState label={`No news between ${str(block.start)} and ${str(block.end)}.`} />
    );
  return (
    <ul className="flex flex-col gap-sm list-none p-0 m-0" aria-label="News items">
      {items.map((raw, i) => {
        const item = raw as Bag;
        const publishedAt = str(item.published_at);
        const headline = str(item.headline);
        const summary = str(item.summary);
        const url = str(item.source_url);
        const source = str(item.source);
        const marFlagged = item.mar_flagged === true;
        return (
          <li
            key={i}
            className="rounded-lg border border-border bg-surface px-lg py-md flex flex-col gap-2xs"
          >
            <div className="flex items-baseline gap-sm flex-wrap">
              <span className="t-meta">{formatDateTime(publishedAt)}</span>
              <span className="t-mono text-xs text-text-tertiary">{source}</span>
              {marFlagged && (
                <span
                  className="t-mono text-xs px-xs py-2xs rounded-sm"
                  style={{
                    background: "var(--signal-warning-soft, rgba(202,138,4,0.12))",
                    color: "var(--signal-warning, #ca8a04)",
                  }}
                >
                  MAR
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-sm">
              {url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="t-body font-medium hover:underline inline-flex items-baseline gap-xs"
                >
                  {headline}
                  <ExternalLink size={12} aria-hidden="true" />
                </a>
              ) : (
                <span className="t-body font-medium">{headline}</span>
              )}
            </div>
            {summary && summary !== "None" && (
              <p className="t-small text-text-secondary">{summary}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/* -------------------------------------------------------------- macro */

function MacroView({ block }: { block: Bag | null }) {
  if (block === null) return <EmptyState label="No macro data" />;
  const series = arr(block.series);
  if (series.length === 0)
    return <EmptyState label={`No macro observations as of ${str(block.as_of)}`} />;
  return (
    <Table
      title={`Macro snapshot · ${series.length}`}
      head={["Series", "Value", "Unit", "Source", "Observed"]}
      rows={series.map((raw) => {
        const m = raw as Bag;
        return [
          str(m.series_code),
          formatNumber(num(m.value)),
          str(m.unit),
          str(m.source),
          str(m.observation_date),
        ];
      })}
    />
  );
}

/* -------------------------------------------------------------- attribution */

function AttributionView({ block }: { block: Bag | null }) {
  if (block === null) return <EmptyState label="No attribution data" />;
  const total = num(block.return_pct);
  const bench = num(block.benchmark_return_pct);
  const sector = num(block.sector_return_pct);
  const vsBench = num(block.relative_to_benchmark_pct);
  const vsSector = num(block.relative_to_sector_pct);
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-md">
      <Stat label="Return" value={formatReturnPct(total)} tone={returnTone(total)} />
      <Stat
        label="Benchmark"
        value={formatReturnPct(bench)}
        tone={returnTone(bench)}
      />
      <Stat label="Sector" value={formatReturnPct(sector)} tone={returnTone(sector)} />
      <Stat
        label="vs Benchmark"
        value={formatReturnPct(vsBench)}
        tone={returnTone(vsBench)}
        meta="excess return"
      />
      <Stat
        label="vs Sector"
        value={formatReturnPct(vsSector)}
        tone={returnTone(vsSector)}
        meta="excess return"
      />
    </div>
  );
}

/* -------------------------------------------------------------- table + utils */

type Cell = string | { value: string; tone: "default" | "positive" | "negative" };

function Table({
  title,
  head,
  rows,
}: {
  title: string;
  head: string[];
  rows: Cell[][];
}) {
  return (
    <section className="flex flex-col gap-sm" aria-label={title}>
      <span className="t-meta">{title}</span>
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted">
            <tr>
              {head.map((h, i) => (
                <th
                  key={i}
                  className="text-left t-meta px-md py-sm whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr
                key={ri}
                className={ri % 2 === 0 ? "bg-surface" : "bg-surface-muted"}
              >
                {row.map((cell, ci) => {
                  if (typeof cell === "string") {
                    return (
                      <td key={ci} className="px-md py-sm t-mono tabular-nums">
                        {cell || "—"}
                      </td>
                    );
                  }
                  const tone =
                    cell.tone === "positive"
                      ? "text-signal-positive"
                      : cell.tone === "negative"
                        ? "text-signal-negative"
                        : "";
                  return (
                    <td
                      key={ci}
                      className={`px-md py-sm t-mono tabular-nums ${tone}`}
                    >
                      {cell.value || "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EmptyState({
  label,
  title,
  body,
}: {
  label?: string;
  title?: string;
  body?: string;
}) {
  if (title !== undefined || body !== undefined) {
    return (
      <div className="rounded-lg border border-border bg-surface px-lg py-md flex flex-col gap-2xs">
        {title !== undefined && <span className="t-label">{title}</span>}
        {body !== undefined && (
          <p className="t-small text-text-tertiary">{body}</p>
        )}
      </div>
    );
  }
  return (
    <p className="t-small text-text-tertiary rounded-lg border border-border bg-surface px-lg py-md">
      {label}
    </p>
  );
}

function pick(data: Record<string, unknown>, key: string): Bag | null {
  const value = data[key];
  if (value === undefined || value === null) return null;
  if (typeof value !== "object") return null;
  return value as Bag;
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function str(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function arr(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function formatPrice(n: number | null): string {
  if (n === null) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatInt(n: number | null): string {
  if (n === null) return "—";
  return Math.round(n).toLocaleString("en-US");
}

function formatNumber(n: number | null): string {
  if (n === null) return "—";
  if (Math.abs(n) >= 1000) {
    return n.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

function formatReturnPct(n: number | null): string {
  if (n === null) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function returnTone(n: number | null): "default" | "positive" | "negative" {
  if (n === null || n === 0) return "default";
  return n > 0 ? "positive" : "negative";
}

function formatDateTime(value: string): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}
