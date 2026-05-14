interface SourceRef {
  id?: string;
  kind?: string;
  description?: string;
  url?: string | null;
}

interface SourceRefListProps {
  sources: readonly Record<string, unknown>[];
}

/**
 * One Tier-2 source per row: kind chip on the left, description on the
 * right (truncated, full text on hover). External URLs collapse onto
 * the description as a link.
 */
export function SourceRefList({ sources }: SourceRefListProps) {
  if (sources.length === 0) {
    return <p className="t-small text-text-tertiary">No sources.</p>;
  }
  return (
    <ul className="flex flex-col gap-2xs list-none p-0 m-0">
      {sources.map((s, i) => {
        const ref = s as SourceRef;
        const label = ref.description ?? ref.id ?? `source-${i}`;
        return (
          <li
            key={ref.id ?? i}
            className="flex items-center gap-sm py-2xs"
            title={label}
          >
            {ref.kind !== undefined && ref.kind.length > 0 ? (
              <span className="inline-flex items-center h-control-sm px-md rounded-pill border border-border bg-surface text-text-secondary text-2xs font-medium uppercase tracking-[0.06em] shrink-0">
                {humaniseKind(ref.kind)}
              </span>
            ) : (
              <span className="inline-flex h-control-sm w-control-sm" aria-hidden="true" />
            )}
            {ref.url ? (
              <a
                href={ref.url}
                target="_blank"
                rel="noreferrer noopener"
                className="t-small underline text-text-primary truncate flex-1 min-w-0"
              >
                {label}
              </a>
            ) : (
              <span className="t-small text-text-secondary truncate flex-1 min-w-0">
                {label}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function humaniseKind(kind: string): string {
  return kind.replace(/_/g, " ");
}
