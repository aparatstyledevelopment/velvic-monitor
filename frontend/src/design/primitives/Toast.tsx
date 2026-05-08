import type { ReactNode } from "react";

type Variant = "info" | "warning" | "negative";

const variantClasses: Record<Variant, string> = {
  info: "border-border bg-surface text-text-primary",
  warning: "border-border bg-track text-text-primary",
  negative: "border-border bg-surface text-text-primary",
};

const accentClasses: Record<Variant, string> = {
  info: "bg-text-secondary",
  warning: "bg-signal-negative",
  negative: "bg-signal-negative",
};

export interface ToastProps {
  variant?: Variant;
  title?: string;
  children: ReactNode;
  onDismiss?: () => void;
  className?: string;
}

export function Toast({
  variant = "info",
  title,
  children,
  onDismiss,
  className = "",
}: ToastProps) {
  const classes = [
    "flex items-start gap-md",
    "rounded-md border px-md py-sm",
    variantClasses[variant],
    className,
  ].join(" ");
  return (
    <div role="status" aria-live="polite" className={classes}>
      <span
        aria-hidden="true"
        className={["mt-[6px] h-2 w-2 rounded-pill shrink-0", accentClasses[variant]].join(" ")}
      />
      <div className="flex-1 min-w-0">
        {title !== undefined && <div className="t-section text-[14px] mb-xxs">{title}</div>}
        <div className="t-small text-text-secondary">{children}</div>
      </div>
      {onDismiss !== undefined && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="text-text-tertiary hover:text-text-primary text-[12px]"
        >
          ×
        </button>
      )}
    </div>
  );
}
