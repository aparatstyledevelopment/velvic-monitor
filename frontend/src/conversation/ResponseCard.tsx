import type { ChatTurnOut } from "../api/chat";
import { Card } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";

import { renderWithCitations, type CitationSpan } from "./citationRenderer";

export interface ToolEvent {
  id: string;
  name: string;
  status: "pending" | "done" | "error";
}

export interface ResponseCardData {
  text: string;
  citation_spans: readonly CitationSpan[];
  finish_reason: string | null;
  warning: string | null;
  streaming: boolean;
  runningTool: string | null;
  toolEvents: readonly ToolEvent[];
  suggested_followups: readonly string[];
}

export function responseCardFromTurn(turn: ChatTurnOut): ResponseCardData {
  return {
    text: turn.content,
    citation_spans: turn.citation_spans ?? [],
    finish_reason: turn.finish_reason ?? null,
    warning: turn.warning ?? null,
    streaming: false,
    runningTool: null,
    toolEvents: [],
    suggested_followups: turn.suggested_followups ?? [],
  };
}

interface ResponseCardProps {
  data: ResponseCardData;
}

export function ResponseCard({ data }: ResponseCardProps) {
  const loadById = useArtifacts((s) => s.loadById);
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const isRefusal = data.finish_reason === "refusal";

  async function onCite(engineCallId: string) {
    openMobile();
    await loadById(engineCallId);
  }

  const hasCitations = data.citation_spans.length > 0;

  const header =
    isRefusal || data.streaming || hasCitations ? (
      <span className="t-meta flex items-center gap-sm">
        {isRefusal ? (
          "Off-topic"
        ) : data.streaming ? (
          <TypingIndicator />
        ) : (
          "Assistant"
        )}
      </span>
    ) : null;

  const bodyClasses = isRefusal
    ? "t-body italic text-text-secondary whitespace-pre-wrap"
    : "t-body whitespace-pre-wrap";

  return (
    <Card header={header ?? undefined}>
      {data.toolEvents.length > 0 && <ToolTimeline events={data.toolEvents} />}
      {data.text.length === 0 && data.streaming ? (
        data.toolEvents.length === 0 && (
          <p className="t-small text-text-tertiary italic">Thinking&hellip;</p>
        )
      ) : (
        <p className={bodyClasses}>
          {renderWithCitations({
            text: data.text,
            spans: data.citation_spans,
            onCite,
          })}
        </p>
      )}
      {data.warning !== null && <WarningRow warning={data.warning} />}
    </Card>
  );
}

function ToolTimeline({ events }: { events: readonly ToolEvent[] }) {
  return (
    <ul
      className="flex flex-col gap-xxs mb-sm pb-sm border-b border-border list-none p-0 m-0"
      aria-label="Tool calls"
    >
      {events.map((ev) => (
        <li key={ev.id} className="flex items-center gap-xs t-small">
          <StatusGlyph status={ev.status} />
          <code className="t-mono text-xs text-text-secondary">{ev.name}</code>
          <span className="text-text-tertiary">{labelFor(ev.status)}</span>
        </li>
      ))}
    </ul>
  );
}

function StatusGlyph({ status }: { status: ToolEvent["status"] }) {
  if (status === "pending") {
    return (
      <span
        aria-hidden="true"
        className="h-xs w-xs rounded-pill bg-text-tertiary animate-pulse shrink-0"
      />
    );
  }
  if (status === "error") {
    return (
      <span
        aria-hidden="true"
        className="h-xs w-xs rounded-pill shrink-0"
        style={{ background: "var(--signal-negative)" }}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="h-xs w-xs rounded-pill shrink-0"
      style={{ background: "var(--signal-positive)" }}
    />
  );
}

function labelFor(status: ToolEvent["status"]): string {
  if (status === "pending") return "calling…";
  if (status === "error") return "failed";
  return "done";
}

function WarningRow({ warning }: { warning: string }) {
  const message =
    warning === "uncited_numeric"
      ? "Some numbers in this answer could not be cited; the result is shown best-effort."
      : warning;
  return (
    <div
      role="status"
      className="mt-md flex items-start gap-sm pt-sm border-t border-border"
    >
      <span
        aria-hidden="true"
        className="mt-2xs h-sm w-sm rounded-pill shrink-0"
        style={{ background: "var(--signal-negative)" }}
      />
      <p className="t-small text-text-secondary flex-1">{message}</p>
    </div>
  );
}

function TypingIndicator() {
  return (
    <span aria-label="Streaming response" className="inline-flex gap-xxs">
      <span className="h-xs w-xs rounded-pill bg-text-tertiary animate-pulse" />
      <span
        className="h-xs w-xs rounded-pill bg-text-tertiary animate-pulse"
        style={{ animationDelay: "120ms" }}
      />
      <span
        className="h-xs w-xs rounded-pill bg-text-tertiary animate-pulse"
        style={{ animationDelay: "240ms" }}
      />
    </span>
  );
}

