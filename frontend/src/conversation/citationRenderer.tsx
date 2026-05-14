import type { components } from "@shared/openapi/types";

import { Tooltip } from "../design/primitives";

export type CitationSpan = components["schemas"]["CitationSpanOut"];

interface RenderOpts {
  text: string;
  spans: readonly CitationSpan[];
  onCite: (engineCallId: string) => void;
  onUncited?: (value: string) => void;
}

type Chip =
  | { kind: "cited"; start: number; end: number; engineCallId: string; ordinal: number }
  | { kind: "uncited"; start: number; end: number; value: string };

/**
 * Same financial-number shape the backend uncited detector uses
 * (decimals, thousands-separated, percentages). Avoids list-bullets,
 * single-digit durations, and ISO dates.
 */
const FINANCIAL_NUMBER_RE =
  /(?<!\d)(?:\d+\.\d+%?|\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+%)(?![A-Za-z0-9])/g;
const ISO_DATE_RE = /\b\d{4}-\d{2}-\d{2}\b/g;

export function renderWithCitations({
  text,
  spans,
  onCite,
  onUncited,
}: RenderOpts): React.ReactNode {
  const cited = resolveSpans(text, spans);
  const uncited = onUncited === undefined ? [] : findUncitedRanges(text, cited);
  const chips: Chip[] = [
    ...cited.map(
      (s): Chip => ({
        kind: "cited",
        start: s.start,
        end: s.end,
        engineCallId: s.engineCallId,
        ordinal: s.ordinal,
      }),
    ),
    ...uncited.map(
      (u): Chip => ({
        kind: "uncited",
        start: u.start,
        end: u.end,
        value: u.value,
      }),
    ),
  ].sort((a, b) => a.start - b.start || a.end - b.end);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < chips.length; i++) {
    const chip = chips[i];
    if (chip === undefined) continue;
    if (chip.start > cursor) {
      nodes.push(text.slice(cursor, chip.start));
    }
    nodes.push(text.slice(chip.start, chip.end));
    if (chip.kind === "cited" && !isSameCitedAsNext(chips, i)) {
      nodes.push(
        <CitationChip
          key={`chip-${i}`}
          engineCallId={chip.engineCallId}
          ordinal={chip.ordinal}
          onCite={onCite}
        />,
      );
    } else if (chip.kind === "uncited" && onUncited !== undefined) {
      nodes.push(
        <UncitedChip
          key={`uncited-${i}`}
          value={chip.value}
          onClick={onUncited}
        />,
      );
    }
    cursor = chip.end;
  }
  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return nodes;
}

function isSameCitedAsNext(chips: readonly Chip[], i: number): boolean {
  const a = chips[i];
  const b = chips[i + 1];
  if (!a || !b) return false;
  if (a.kind !== "cited" || b.kind !== "cited") return false;
  if (a.engineCallId !== b.engineCallId) return false;
  if (b.start !== a.end) return false;
  return true;
}

interface ResolvedSpan {
  start: number;
  end: number;
  engineCallId: string;
  ordinal: number;
}

export function resolveSpans(
  text: string,
  spans: readonly CitationSpan[],
): ResolvedSpan[] {
  const filtered = spans.filter(
    (s) =>
      s.start_char < s.end_char && s.start_char >= 0 && s.end_char <= text.length,
  );
  const sorted = [...filtered].sort((a, b) => a.start_char - b.start_char);
  const ordinalById = new Map<string, number>();
  let nextOrdinal = 1;
  const resolved: ResolvedSpan[] = [];
  for (const s of sorted) {
    let ord = ordinalById.get(s.engine_call_id);
    if (ord === undefined) {
      ord = nextOrdinal;
      nextOrdinal += 1;
      ordinalById.set(s.engine_call_id, ord);
    }
    resolved.push({
      start: s.start_char,
      end: s.end_char,
      engineCallId: s.engine_call_id,
      ordinal: ord,
    });
  }
  return resolved;
}

function findUncitedRanges(
  text: string,
  cited: readonly ResolvedSpan[],
): { start: number; end: number; value: string }[] {
  const isoDates: { start: number; end: number }[] = [];
  for (const m of text.matchAll(ISO_DATE_RE)) {
    if (m.index === undefined) continue;
    isoDates.push({ start: m.index, end: m.index + m[0].length });
  }
  const out: { start: number; end: number; value: string }[] = [];
  for (const m of text.matchAll(FINANCIAL_NUMBER_RE)) {
    if (m.index === undefined) continue;
    const start = m.index;
    const end = m.index + m[0].length;
    if (cited.some((c) => c.start <= start && end <= c.end)) continue;
    if (isoDates.some((d) => d.start <= start && end <= d.end)) continue;
    out.push({ start, end, value: m[0] });
  }
  return out;
}

interface CitationChipProps {
  engineCallId: string;
  ordinal: number;
  onCite: (engineCallId: string) => void;
}

export function CitationChip({ engineCallId, ordinal, onCite }: CitationChipProps) {
  return (
    <Tooltip label={`engine_call ${engineCallId}`}>
      <button
        type="button"
        onClick={() => onCite(engineCallId)}
        className="inline-flex items-center justify-center align-baseline ml-xxs h-lg min-w-lg px-xs text-2xs font-medium rounded-pill bg-track text-text-secondary hover:bg-text-primary hover:text-surface transition-colors duration-fast"
        data-engine-call-id={engineCallId}
        aria-label={`Open evidence ${ordinal}`}
      >
        {ordinal}
      </button>
    </Tooltip>
  );
}

interface UncitedChipProps {
  value: string;
  onClick: (value: string) => void;
}

export function UncitedChip({ value, onClick }: UncitedChipProps) {
  return (
    <Tooltip label="No source — click for details">
      <button
        type="button"
        onClick={() => onClick(value)}
        aria-label={`No source for "${value}"`}
        className="inline-flex items-center justify-center align-baseline ml-xxs h-lg min-w-lg px-xs text-2xs font-semibold rounded-pill transition-colors duration-fast"
        style={{
          background: "var(--signal-negative-soft, rgba(220,38,38,0.12))",
          color: "var(--signal-negative, #dc2626)",
        }}
      >
        !
      </button>
    </Tooltip>
  );
}
