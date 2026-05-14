import type { EngineCallEnvelope } from "../state/artifacts";
import { Hairline, Sparkline } from "../design/primitives";

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
