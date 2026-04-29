import type { ReactNode } from "react";

export function Pill({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-xs",
        "h-6 px-md rounded-pill",
        "border border-border bg-surface",
        "text-[12px] text-text-secondary",
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
