interface GenericTableProps {
  data: Record<string, unknown>;
}

export function GenericTable({ data }: GenericTableProps) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <p className="t-small text-text-tertiary">No data.</p>;
  }
  return (
    <dl className="grid grid-cols-[minmax(96px,auto)_1fr] gap-x-md gap-y-xs">
      {entries.map(([key, value]) => (
        <Row key={key} k={key} v={value} />
      ))}
    </dl>
  );
}

function Row({ k, v }: { k: string; v: unknown }) {
  return (
    <>
      <dt className="t-meta self-start pt-xxs">{k}</dt>
      <dd className="t-mono text-sm break-all whitespace-pre-wrap">{formatValue(v)}</dd>
    </>
  );
}

function formatValue(v: unknown): string {
  if (v === null) return "null";
  if (v === undefined) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, "");
  }
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "true" : "false";
  return JSON.stringify(v);
}
