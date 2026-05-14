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
      className="flex flex-col rounded-lg border border-border bg-surface px-xl py-lg gap-lg"
      aria-busy="true"
      aria-live="polite"
      aria-label={`Loading source ${engineCallId.slice(-8)}`}
    >
      {/* Header: title + subtitle */}
      <div className="flex flex-col gap-2xs">
        <span className="h-xl w-1/2 rounded-md bg-surface-muted animate-pulse" />
        <span className="h-md w-1/3 rounded-md bg-surface-muted animate-pulse" />
      </div>
      {/* Description paragraph */}
      <div className="flex flex-col gap-2xs">
        <span className="h-md w-full rounded-pill bg-surface-muted animate-pulse" />
        <span className="h-md w-4/5 rounded-pill bg-surface-muted animate-pulse" />
      </div>
      {/* Query block */}
      <div className="flex flex-col gap-xs">
        <span className="h-sm w-1/6 rounded-pill bg-surface-muted animate-pulse" />
        <span className="h-control-xl w-full rounded-md bg-surface-muted animate-pulse" />
      </div>
      {/* Response block */}
      <div className="flex flex-col gap-xs">
        <span className="h-sm w-1/6 rounded-pill bg-surface-muted animate-pulse" />
        <span className="h-control-xl w-full rounded-md bg-surface-muted animate-pulse" />
      </div>
    </article>
  );
}
