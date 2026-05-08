import type { ChatTurnOut } from "../api/chat";
import { engineCallsApi } from "../api/engineCalls";
import { Card, Pill } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";

import { renderWithCitations, type CitationSpan } from "./citationRenderer";

export interface ResponseCardData {
  text: string;
  citation_spans: readonly CitationSpan[];
  finish_reason: string | null;
  warning: string | null;
  streaming: boolean;
  runningTool: string | null;
}

export function responseCardFromTurn(turn: ChatTurnOut): ResponseCardData {
  return {
    text: turn.content,
    citation_spans: turn.citation_spans ?? [],
    finish_reason: turn.finish_reason ?? null,
    warning: turn.warning ?? null,
    streaming: false,
    runningTool: null,
  };
}

interface ResponseCardProps {
  data: ResponseCardData;
}

export function ResponseCard({ data }: ResponseCardProps) {
  const push = useArtifacts((s) => s.push);
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const isRefusal = data.finish_reason === "refusal";

  async function onCite(engineCallId: string) {
    const envelope = await engineCallsApi.get(engineCallId);
    push(envelope);
    openMobile();
  }

  const header = isRefusal ? (
    <span className="t-meta">Off-topic</span>
  ) : data.streaming ? (
    <span className="t-meta flex items-center gap-sm">
      <TypingIndicator />
      {data.runningTool !== null && (
        <Pill className="t-mono">engine: {data.runningTool}</Pill>
      )}
    </span>
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
        className="mt-[6px] h-2 w-2 rounded-pill shrink-0"
        style={{ background: "var(--signal-negative)" }}
      />
      <p className="t-small text-text-secondary flex-1">{message}</p>
    </div>
  );
}

function TypingIndicator() {
  return (
    <span aria-label="Streaming response" className="inline-flex gap-[3px]">
      <span className="h-[4px] w-[4px] rounded-pill bg-text-tertiary animate-pulse" />
      <span
        className="h-[4px] w-[4px] rounded-pill bg-text-tertiary animate-pulse"
        style={{ animationDelay: "120ms" }}
      />
      <span
        className="h-[4px] w-[4px] rounded-pill bg-text-tertiary animate-pulse"
        style={{ animationDelay: "240ms" }}
      />
    </span>
  );
}
