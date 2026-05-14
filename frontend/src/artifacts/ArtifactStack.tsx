import { useArtifacts } from "../state/artifacts";

import { ArtifactCard, ArtifactRow, UncitedCard } from "./ArtifactCard";

export function ArtifactStack() {
  const entries = useArtifacts((s) => s.entries);
  const viewMode = useArtifacts((s) => s.viewMode);
  const toggleExpanded = useArtifacts((s) => s.toggleExpanded);

  if (entries.length === 0) {
    return (
      <p className="t-small text-text-tertiary">
        Click a citation chip to inspect the deterministic engine call behind a
        number, or use the Source button to browse every source for a response.
      </p>
    );
  }

  if (viewMode === "single") {
    const entry = entries[0];
    if (entry === undefined) return null;
    if (entry.kind === "uncited") {
      return <UncitedCard value={entry.value} />;
    }
    if (entry.envelope === null) {
      return <ArtifactSkeleton engineCallId={entry.engine_call_id} />;
    }
    return <ArtifactCard envelope={entry.envelope} />;
  }

  return (
    <div className="flex flex-col gap-xs">
      {entries.map((entry) =>
        entry.kind === "uncited" ? (
          <UncitedCard key={entry.key} value={entry.value} />
        ) : (
          <ArtifactRow
            key={entry.engine_call_id}
            entry={entry}
            onToggle={() => toggleExpanded(entry.engine_call_id)}
          />
        ),
      )}
    </div>
  );
}

function ArtifactSkeleton({ engineCallId }: { engineCallId: string }) {
  return (
    <article
      className="flex flex-col rounded-lg border border-border bg-surface px-xl py-lg gap-lg"
      aria-busy="true"
      aria-live="polite"
      aria-label={`Loading source ${engineCallId.slice(-8)}`}
    >
      <div className="flex flex-col gap-2xs">
        <span className="h-xl w-1/2 rounded-md bg-surface-muted animate-pulse" />
        <span className="h-md w-1/3 rounded-md bg-surface-muted animate-pulse" />
      </div>
      <div className="flex flex-col gap-2xs">
        <span className="h-md w-full rounded-pill bg-surface-muted animate-pulse" />
        <span className="h-md w-4/5 rounded-pill bg-surface-muted animate-pulse" />
      </div>
      <div className="flex flex-col gap-xs">
        <span className="h-sm w-1/6 rounded-pill bg-surface-muted animate-pulse" />
        <span className="h-control-xl w-full rounded-md bg-surface-muted animate-pulse" />
      </div>
    </article>
  );
}
