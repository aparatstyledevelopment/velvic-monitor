interface SourceRef {
  id?: string;
  kind?: string;
  description?: string;
  url?: string | null;
}

interface SourceRefListProps {
  sources: readonly Record<string, unknown>[];
}

export function SourceRefList({ sources }: SourceRefListProps) {
  if (sources.length === 0) {
    return <p className="t-small text-text-tertiary">No sources.</p>;
  }
  return (
    <ul className="flex flex-col gap-xs list-none p-0 m-0">
      {sources.map((s, i) => {
        const ref = s as SourceRef;
        const label = ref.description ?? ref.id ?? `source-${i}`;
        return (
          <li key={ref.id ?? i} className="flex items-baseline gap-sm">
            {ref.kind !== undefined && (
              <span className="t-meta shrink-0">{ref.kind}</span>
            )}
            {ref.url ? (
              <a
                href={ref.url}
                target="_blank"
                rel="noreferrer noopener"
                className="t-small underline text-text-primary truncate"
              >
                {label}
              </a>
            ) : (
              <span className="t-small truncate">{label}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
