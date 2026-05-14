import { formatScalar, humaniseKey } from "../format";

interface RecordsTableProps {
  columns: readonly string[];
  rows: readonly Record<string, unknown>[];
  /** SQL-shaped table where rows are arrays in column order. */
  arrayRows?: readonly unknown[][];
  truncated?: boolean;
}

export function RecordsTable({
  columns,
  rows,
  arrayRows,
  truncated,
}: RecordsTableProps) {
  const displayRows = arrayRows ?? rowsAsArrays(columns, rows);
  if (displayRows.length === 0) {
    return <p className="t-small text-text-tertiary">No rows.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full t-numeric text-sm">
        <thead>
          <tr className="bg-surface-muted text-text-tertiary">
            {columns.map((c) => (
              <th
                key={c}
                scope="col"
                className="text-left font-medium uppercase tracking-[0.06em] px-md py-xs t-meta whitespace-nowrap"
              >
                {humaniseKey(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, i) => (
            <tr key={i} className="border-t border-border first:border-t-0">
              {columns.map((c, j) => (
                <td
                  key={c}
                  className="px-md py-xs align-top whitespace-nowrap text-text-primary"
                >
                  {formatScalar(c, row[j])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {truncated === true && (
        <p className="t-meta px-md py-xs">Truncated · server limit reached</p>
      )}
    </div>
  );
}

function rowsAsArrays(
  columns: readonly string[],
  rows: readonly Record<string, unknown>[],
): unknown[][] {
  return rows.map((row) => columns.map((c) => row[c]));
}
