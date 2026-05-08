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
  return (
    <article className={classes}>
      {header !== undefined && (
        <header className="flex items-center justify-between gap-md px-lg py-md border-b border-border">
          {header}
        </header>
      )}
      <div className="flex-1 px-lg py-md">{children}</div>
      {footer !== undefined && (
        <footer className="px-lg py-md border-t border-border t-meta">{footer}</footer>
      )}
    </article>
  );
}
