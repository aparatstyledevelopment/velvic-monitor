import { AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";

import { Hairline, Sparkline } from "../design/primitives";
import type {
  EngineCallEntry,
  EngineCallEnvelope,
} from "../state/artifacts";

import {
  describeArtifact,
  humaniseKey,
  inspectResponse,
  renderFunctionCall,
  toolMeta,
} from "./format";
import { CodeBlock } from "./renderers/CodeBlock";
import { FieldList } from "./renderers/FieldList";
import { RecordsTable } from "./renderers/RecordsTable";
import { SourceRefList } from "./renderers/SourceRefList";

interface ArtifactCardProps {
  envelope: EngineCallEnvelope;
}

export function ArtifactCard({ envelope }: ArtifactCardProps) {
  const meta = toolMeta(envelope.tool_name);
  const description = describeArtifact(envelope);
  const response = inspectResponse(envelope);
  const isAdHocSql = response.kind === "sql";
  const queryTitle = isAdHocSql ? "SQL" : "Query";
  const responseRowCount = rowCount(response);

  return (
    <article
      className="flex flex-col rounded-lg border border-border bg-surface px-xl py-lg gap-lg"
      aria-label={meta.title}
    >
      <header className="flex flex-col gap-2xs">
        <h3 className="t-title text-2xl">{meta.title}</h3>
        <p className="t-small text-text-tertiary">
          Source data view · {meta.category}
          {envelope.module !== meta.category.toLowerCase() && (
            <> → {humaniseModule(envelope.module)}</>
          )}
        </p>
      </header>

      {description !== null && (
        <>
          <Hairline />
          <p className="t-body">{description}</p>
        </>
      )}

      <Section title={queryTitle}>
        {isAdHocSql ? (
          <CodeBlock ariaLabel="SQL query" language="sql">
            {response.sql}
          </CodeBlock>
        ) : (
          <CodeBlock ariaLabel="Engine call">
            {renderFunctionCall(envelope.tool_name, envelope.params)}
          </CodeBlock>
        )}
      </Section>

      <Section
        title="Response"
        {...(responseRowCount === null
          ? {}
          : {
              meta: `${responseRowCount} row${responseRowCount === 1 ? "" : "s"}`,
            })}
      >
        <ResponseBody envelope={envelope} />
      </Section>

      {envelope.sources.length > 0 && (
        <Section title="Sources">
          <SourceRefList
            sources={envelope.sources as Record<string, unknown>[]}
          />
        </Section>
      )}
    </article>
  );
}

/**
 * Collapsed row used in list mode (Source button). Click toggles to a full
 * expanded ArtifactCard rendered inline underneath the row header.
 */
export function ArtifactRow({
  entry,
  onToggle,
}: {
  entry: EngineCallEntry;
  onToggle: () => void;
}) {
  const label = entry.envelope
    ? toolMeta(entry.envelope.tool_name).title
    : "Loading…";
  const description = entry.envelope ? describeArtifact(entry.envelope) : null;
  const idTail = entry.engine_call_id.slice(-8);

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={entry.expanded}
        aria-label={`${entry.expanded ? "Collapse" : "Expand"} ${label}`}
        className="w-full flex items-center gap-md px-lg py-md text-left hover:bg-surface-muted transition-colors"
      >
        <span aria-hidden="true" className="shrink-0 text-text-tertiary">
          {entry.expanded ? (
            <ChevronDown size={16} />
          ) : (
            <ChevronRight size={16} />
          )}
        </span>
        <div className="flex-1 min-w-0 flex flex-col gap-2xs">
          <span className="t-label truncate">{label}</span>
          {description !== null && (
            <span className="t-small text-text-tertiary truncate">
              {description}
            </span>
          )}
        </div>
        <code className="t-mono text-xs text-text-tertiary shrink-0">
          ec_…{idTail}
        </code>
      </button>
      {entry.expanded && entry.envelope !== null && (
        <div className="border-t border-border">
          <ArtifactCard envelope={entry.envelope} />
        </div>
      )}
      {entry.expanded && entry.envelope === null && entry.error === null && (
        <div className="border-t border-border px-lg py-md">
          <p className="t-small text-text-tertiary">Loading source&hellip;</p>
        </div>
      )}
      {entry.error !== null && (
        <div className="border-t border-border px-lg py-md">
          <p className="t-small text-text-tertiary">{entry.error}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Placeholder shown when the user clicks the red "!" chip behind a
 * number the model emitted without a citation. The model surfaced a
 * value that doesn't trace to an engine call — there is no deterministic
 * source behind it, and the answer should be treated as best-effort.
 */
export function UncitedCard({ value }: { value: string }) {
  return (
    <article
      className="flex flex-col rounded-lg border bg-surface px-xl py-lg gap-md"
      style={{ borderColor: "var(--signal-negative, #dc2626)" }}
      aria-label={`No source available for ${value}`}
    >
      <header className="flex items-center gap-sm">
        <span
          aria-hidden="true"
          className="inline-flex items-center justify-center"
          style={{ color: "var(--signal-negative, #dc2626)" }}
        >
          <AlertTriangle size={18} />
        </span>
        <h3 className="t-title text-xl">No source available</h3>
      </header>
      <p className="t-body">
        The model produced{" "}
        <code className="t-mono text-sm px-xs py-2xs rounded-sm bg-surface-muted">
          {value}
        </code>{" "}
        without a citation to any deterministic engine call. Treat this number
        as best-effort — the Engine/Narrator contract requires every numerical
        claim to come from a tool result.
      </p>
      <p className="t-small text-text-tertiary">
        If this number is critical, ask a follow-up that scopes the request to
        a specific tool (price move, peer returns, attribution, etc.) so the
        answer is grounded in a fresh engine call.
      </p>
    </article>
  );
}

function Section({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-label={title} className="flex flex-col gap-sm">
      <header className="flex items-baseline justify-between gap-sm">
        <span className="t-meta">{title}</span>
        {meta !== undefined && (
          <span className="t-meta normal-case tracking-normal text-text-tertiary">
            {meta}
          </span>
        )}
      </header>
      {children}
    </section>
  );
}

function ResponseBody({ envelope }: { envelope: EngineCallEnvelope }) {
  const response = inspectResponse(envelope);
  switch (response.kind) {
    case "sql":
      return (
        <RecordsTable
          columns={response.columns}
          rows={[]}
          arrayRows={response.rows as unknown[][]}
        />
      );
    case "records":
      return (
        <div className="flex flex-col gap-md">
          {response.scalars.length > 0 && (
            <FieldList entries={response.scalars} />
          )}
          {response.series !== null && (
            <figure
              className="flex flex-col gap-xs rounded-md border border-border bg-surface-muted px-lg py-md"
              aria-label={`${humaniseKey(response.series.valueColumn)} trend`}
            >
              <figcaption className="t-meta">
                {humaniseKey(response.series.valueColumn)} trend
              </figcaption>
              <Sparkline
                values={response.series.values}
                width={320}
                height={64}
                ariaLabel={`${humaniseKey(response.series.valueColumn)} sparkline`}
                className="w-full h-auto"
              />
            </figure>
          )}
          <RecordsTable columns={response.columns} rows={response.rows} />
        </div>
      );
    case "fields":
      return <FieldList entries={response.scalars} />;
    case "json":
      return (
        <pre className="t-mono text-sm leading-relaxed whitespace-pre-wrap rounded-md border border-border bg-surface-muted px-lg py-md overflow-x-auto">
          {JSON.stringify(response.raw, null, 2)}
        </pre>
      );
  }
}

function rowCount(
  response: ReturnType<typeof inspectResponse>,
): number | null {
  if (response.kind === "sql") return response.rows.length;
  if (response.kind === "records") return response.rows.length;
  return null;
}

function humaniseModule(m: string): string {
  if (m.length === 0) return m;
  return m.charAt(0).toUpperCase() + m.slice(1);
}
