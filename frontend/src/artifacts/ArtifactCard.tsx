import type { EngineCallEnvelope } from "../state/artifacts";
import { Card, Pill } from "../design/primitives";

import { GenericTable } from "./renderers/GenericTable";
import { SourceRefList } from "./renderers/SourceRefList";

interface ArtifactCardProps {
  envelope: EngineCallEnvelope;
}

export function ArtifactCard({ envelope }: ArtifactCardProps) {
  const shortId = envelope.engine_call_id.slice(-8);

  return (
    <Card
      header={
        <>
          <div className="flex items-center gap-sm min-w-0">
            <Pill>{envelope.tool_name}</Pill>
            <span className="t-mono text-xs text-text-tertiary truncate">
              {shortId}
            </span>
          </div>
        </>
      }
      footer={
        <span className="flex items-center gap-md text-text-tertiary">
          <span>{envelope.latency_ms}ms</span>
          <span>{envelope.engine_version}</span>
          <span className="ml-auto">{formatTimestamp(envelope.computed_at)}</span>
        </span>
      }
    >
      <Section title="Params">
        <GenericTable data={envelope.params} />
      </Section>
      <Section title="Result">
        <GenericTable data={envelope.data} />
      </Section>
      <Section title="Sources">
        <SourceRefList sources={envelope.sources as Record<string, unknown>[]} />
      </Section>
    </Card>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-md last:mb-0">
      <div className="t-meta mb-xs">{title}</div>
      {children}
    </div>
  );
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace("T", " ");
}
