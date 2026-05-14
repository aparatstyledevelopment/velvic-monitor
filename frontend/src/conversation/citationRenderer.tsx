import type { components } from "@shared/openapi/types";

import { Tooltip } from "../design/primitives";

export type CitationSpan = components["schemas"]["CitationSpanOut"];

interface RenderOpts {
  text: string;
  spans: readonly CitationSpan[];
  onCite: (engineCallId: string) => void;
}

interface ResolvedSpan {
  start: number;
  end: number;
  engineCallId: string;
  ordinal: number;
}

export function renderWithCitations({ text, spans, onCite }: RenderOpts): React.ReactNode {
  const resolved = resolveSpans(text, spans);
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < resolved.length; i++) {
    const span = resolved[i];
    if (!span) continue;
    if (span.start > cursor) {
      nodes.push(text.slice(cursor, span.start));
    }
    nodes.push(text.slice(span.start, span.end));
    if (!isSameAsNext(resolved, i)) {
      nodes.push(
        <CitationChip
          key={`chip-${i}`}
          engineCallId={span.engineCallId}
          ordinal={span.ordinal}
          onCite={onCite}
        />,
      );
    }
    cursor = span.end;
  }
  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return nodes;
}

function isSameAsNext(spans: readonly ResolvedSpan[], i: number): boolean {
  const a = spans[i];
  const b = spans[i + 1];
  if (!a || !b) return false;
  if (a.engineCallId !== b.engineCallId) return false;
  if (b.start !== a.end) return false;
  return true;
}

export function resolveSpans(
  text: string,
  spans: readonly CitationSpan[],
): ResolvedSpan[] {
  const filtered = spans.filter(
    (s) => s.start_char < s.end_char && s.start_char >= 0 && s.end_char <= text.length,
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
