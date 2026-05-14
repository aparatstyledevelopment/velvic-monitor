import type { ReactNode } from "react";

interface StatProps {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  meta?: ReactNode;
  tone?: "default" | "positive" | "negative";
  className?: string;
}

const toneClasses: Record<NonNullable<StatProps["tone"]>, string> = {
  default: "text-text-primary",
  positive: "text-signal-positive",
  negative: "text-signal-negative",
};

export function Stat({
  label,
  value,
  delta,
  meta,
  tone = "default",
  className = "",
}: StatProps) {
  return (
    <div
      className={[
        "flex flex-col gap-xxs rounded-lg border border-border bg-surface px-lg py-md min-w-0",
        className,
      ].join(" ")}
    >
      <div className="t-meta">{label}</div>
      <div
        className={[
          "t-numeric text-2xl leading-tight tracking-tight truncate",
          toneClasses[tone],
        ].join(" ")}
      >
        {value}
      </div>
      {(delta !== undefined || meta !== undefined) && (
        <div className="flex items-center gap-sm t-small text-text-tertiary truncate">
          {delta}
          {meta}
        </div>
      )}
    </div>
  );
}
