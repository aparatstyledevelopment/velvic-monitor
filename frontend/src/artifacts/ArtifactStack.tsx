import { useArtifacts } from "../state/artifacts";

import { ArtifactCard } from "./ArtifactCard";

export function ArtifactStack() {
  const stack = useArtifacts((s) => s.stack);
  const loadingIds = useArtifacts((s) => s.loadingIds);
  const loading = Array.from(loadingIds);

  if (stack.length === 0 && loading.length === 0) {
    return (
      <p className="t-small text-text-tertiary">
        Click a citation chip to inspect the deterministic engine call behind a number.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-md">
      {loading.map((id) => (
        <ArtifactSkeleton key={`loading-${id}`} engineCallId={id} />
      ))}
      {stack.map((envelope) => (
        <ArtifactCard key={envelope.engine_call_id} envelope={envelope} />
      ))}
    </div>
  );
}

function ArtifactSkeleton({ engineCallId }: { engineCallId: string }) {
  return (
    <article
      className="flex flex-col rounded-lg border border-border bg-surface px-xl py-lg gap-sm"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="flex items-center gap-sm">
        <span className="h-control-sm w-1/4 rounded-pill bg-surface-muted animate-pulse" />
        <span className="t-mono text-xs text-text-tertiary truncate">
          {engineCallId.slice(-8)}
        </span>
      </div>
      <span className="h-xs w-full rounded-pill bg-surface-muted animate-pulse" />
      <span className="h-xs w-3/4 rounded-pill bg-surface-muted animate-pulse" />
      <span className="h-xs w-2/3 rounded-pill bg-surface-muted animate-pulse" />
    </article>
  );
}
