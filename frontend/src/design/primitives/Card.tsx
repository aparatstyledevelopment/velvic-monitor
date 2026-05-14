import type { ReactNode } from "react";

interface CardProps {
  header?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ header, footer, children, className = "" }: CardProps) {
  const classes = [
    "flex flex-col rounded-lg border border-border bg-surface",
    "overflow-hidden",
    className,
  ].join(" ");
  const hasHeader = header !== undefined;
  // Editorial spacing: generous padding, no inner divider — separation
  // comes from whitespace, not borderlines.
  const bodyClasses = hasHeader
    ? "flex-1 px-xl pb-xl pt-md"
    : "flex-1 p-xl";
  return (
    <article className={classes}>
      {hasHeader && (
        <header className="flex items-center justify-between gap-md px-xl pt-lg pb-md">
          {header}
        </header>
      )}
      <div className={bodyClasses}>{children}</div>
      {footer !== undefined && (
        <footer className="px-xl py-md border-t border-border t-meta">
          {footer}
        </footer>
      )}
    </article>
  );
}
