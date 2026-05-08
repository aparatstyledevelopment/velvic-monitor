import { useArtifacts } from "../state/artifacts";

import { ArtifactCard } from "./ArtifactCard";

export function ArtifactStack() {
  const stack = useArtifacts((s) => s.stack);
  if (stack.length === 0) {
    return (
      <p className="t-small text-text-tertiary">
        Click a citation chip to inspect the deterministic engine call behind a number.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-md">
      {stack.map((envelope) => (
        <ArtifactCard key={envelope.engine_call_id} envelope={envelope} />
      ))}
    </div>
  );
}
