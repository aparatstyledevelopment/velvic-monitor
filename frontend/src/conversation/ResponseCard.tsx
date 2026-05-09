import type { ChatTurnOut } from "../api/chat";
import { engineCallsApi } from "../api/engineCalls";
import { Card, Pill, PillButton } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { useComposer } from "../state/composer";

import { renderWithCitations, type CitationSpan } from "./citationRenderer";

export interface ResponseCardData {
  text: string;
  citation_spans: readonly CitationSpan[];
  finish_reason: string | null;
  warning: string | null;
  streaming: boolean;
  runningTool: string | null;
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
    suggested_followups: turn.suggested_followups ?? [],
  };
}

interface ResponseCardProps {
  data: ResponseCardData;
}

export function ResponseCard({ data }: ResponseCardProps) {
  const push = useArtifacts((s) => s.push);
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const setDraft = useComposer((s) => s.setDraft);
  const isRefusal = data.finish_reason === "refusal";

  async function onCite(engineCallId: string) {
    const envelope = await engineCallsApi.get(engineCallId);
    push(envelope);
    openMobile();
  }

  async function onOpenPrimarySource() {
    const first = data.citation_spans[0]?.engine_call_id;
    if (first === undefined) return;
    await onCite(first);
  }

  const hasCitations = data.citation_spans.length > 0;

  const header =
    isRefusal || data.streaming || hasCitations ? (
      <>
        <span className="t-meta flex items-center gap-sm">
          {isRefusal ? (
            "Off-topic"
          ) : data.streaming ? (
            <>
              <TypingIndicator />
              {data.runningTool !== null && (
                <Pill tone="muted" className="t-mono">
                  engine: {data.runningTool}
                </Pill>
              )}
            </>
          ) : (
            "Assistant"
          )}
        </span>
        {hasCitations && !data.streaming && (
          <PillButton tone="inverse" onClick={onOpenPrimarySource}>
            Source
          </PillButton>
        )}
      </>
    ) : null;

  const bodyClasses = isRefusal
    ? "t-body italic text-text-secondary whitespace-pre-wrap"
    : "t-body whitespace-pre-wrap";

  return (
    <Card header={header ?? undefined}>
      {data.text.length === 0 && data.streaming ? (
        <p className="t-small text-text-tertiary italic">Thinking&hellip;</p>
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
      {!data.streaming &&
        !isRefusal &&
        data.suggested_followups.length > 0 && (
          <div className="mt-md flex flex-wrap gap-xs pt-md border-t border-border">
            {data.suggested_followups.map((s, i) => (
              <PillButton
                key={i}
                onClick={() => setDraft(s)}
                aria-label={`Use follow-up: ${s}`}
              >
                {s}
              </PillButton>
            ))}
          </div>
        )}
    </Card>
  );
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
