import { formatScalar, humaniseKey } from "../format";

interface FieldListProps {
  entries: readonly [string, unknown][];
  /**
   * Skip keys whose primary content has already been promoted into the
   * description (e.g. ticker, dates) to avoid double-printing.
   */
  hideKeys?: ReadonlySet<string>;
}

export function FieldList({ entries, hideKeys }: FieldListProps) {
  const visible = hideKeys
    ? entries.filter(([k]) => !hideKeys.has(k))
    : entries;
  if (visible.length === 0) {
    return <p className="t-small text-text-tertiary">No fields.</p>;
  }
  return (
    <dl className="grid grid-cols-[minmax(96px,auto)_1fr] gap-x-md gap-y-xs">
      {visible.map(([k, v]) => (
        <FieldRow key={k} k={k} v={v} />
      ))}
    </dl>
  );
}

function FieldRow({ k, v }: { k: string; v: unknown }) {
  return (
    <>
      <dt className="t-meta self-start pt-xxs">{humaniseKey(k)}</dt>
      <dd className="t-numeric text-base break-words">{formatScalar(k, v)}</dd>
    </>
  );
}
