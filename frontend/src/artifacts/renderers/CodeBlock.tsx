import { Fragment, type ReactNode } from "react";

interface CodeBlockProps {
  /** Heading is the wrapper aria-label; the visual heading lives outside. */
  ariaLabel?: string;
  /** "sql" applies a tiny token-based SQL highlighter; "plain" passes through. */
  language?: "sql" | "plain";
  children: ReactNode;
}

export function CodeBlock({ ariaLabel, language = "plain", children }: CodeBlockProps) {
  const body =
    language === "sql" && typeof children === "string"
      ? highlightSql(children)
      : children;
  return (
    <pre
      aria-label={ariaLabel}
      className="t-mono text-sm leading-relaxed whitespace-pre-wrap rounded-md border border-border bg-surface-inverted text-surface px-lg py-md overflow-x-auto"
    >
      {body}
    </pre>
  );
}

// Tiny SQL highlighter: keyword / string / number / comment / identifier.
// Order matters: comments + strings first so keywords inside them don't match.
const SQL_KEYWORDS = new Set([
  "SELECT",
  "FROM",
  "WHERE",
  "AND",
  "OR",
  "NOT",
  "IN",
  "IS",
  "NULL",
  "GROUP",
  "BY",
  "ORDER",
  "HAVING",
  "LIMIT",
  "OFFSET",
  "JOIN",
  "LEFT",
  "RIGHT",
  "INNER",
  "OUTER",
  "ON",
  "AS",
  "DISTINCT",
  "UNION",
  "ALL",
  "CASE",
  "WHEN",
  "THEN",
  "ELSE",
  "END",
  "WITH",
  "BETWEEN",
  "LIKE",
  "ILIKE",
  "ASC",
  "DESC",
  "TRUE",
  "FALSE",
  "INTERVAL",
  "COUNT",
  "SUM",
  "AVG",
  "MIN",
  "MAX",
  "ROUND",
  "COALESCE",
  "DATE_TRUNC",
  "EXTRACT",
  "NOW",
  "CURRENT_DATE",
]);

// Single pass: comment | string | number | identifier-or-keyword | other
const SQL_TOKEN = /(--[^\n]*|\/\*[\s\S]*?\*\/)|('(?:[^']|'')*')|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)|([\s\S])/g;

function highlightSql(src: string): ReactNode {
  const nodes: ReactNode[] = [];
  let key = 0;
  let plain = "";
  function flushPlain() {
    if (plain.length > 0) {
      nodes.push(plain);
      plain = "";
    }
  }
  for (const m of src.matchAll(SQL_TOKEN)) {
    const [, comment, str, num, ident, other] = m;
    if (comment !== undefined) {
      flushPlain();
      nodes.push(
        <span key={key++} className="text-text-tertiary italic">
          {comment}
        </span>,
      );
    } else if (str !== undefined) {
      flushPlain();
      nodes.push(
        <span key={key++} style={{ color: "var(--signal-positive)" }}>
          {str}
        </span>,
      );
    } else if (num !== undefined) {
      flushPlain();
      nodes.push(
        <span key={key++} style={{ color: "var(--signal-warning)" }}>
          {num}
        </span>,
      );
    } else if (ident !== undefined) {
      if (SQL_KEYWORDS.has(ident.toUpperCase())) {
        flushPlain();
        nodes.push(
          <span key={key++} className="font-medium" style={{ color: "var(--accent-default)" }}>
            {ident}
          </span>,
        );
      } else {
        plain += ident;
      }
    } else if (other !== undefined) {
      plain += other;
    }
  }
  flushPlain();
  return (
    <>
      {nodes.map((n, i) => (
        <Fragment key={i}>{n}</Fragment>
      ))}
    </>
  );
}
