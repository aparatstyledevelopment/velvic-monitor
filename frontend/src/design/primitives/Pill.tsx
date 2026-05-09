import { forwardRef } from "react";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

type Tone = "default" | "inverse" | "muted";

const toneClasses: Record<Tone, string> = {
  default: "border border-border bg-surface text-text-secondary",
  inverse:
    "border border-surface-inverted bg-surface-inverted text-surface",
  muted: "border border-transparent bg-surface-muted text-text-secondary",
};

const interactiveClasses =
  "transition-[background-color,border-color,opacity] duration-fast ease-standard focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface";

const interactiveToneHover: Record<Tone, string> = {
  default: "hover:border-border-strong hover:bg-surface-muted",
  inverse: "hover:opacity-90 active:opacity-100",
  muted: "hover:bg-track-emphasized",
};

const baseClasses =
  "inline-flex items-center gap-xs h-control-sm px-md rounded-pill text-sm font-medium leading-none";

interface CommonPillProps {
  tone?: Tone;
  className?: string | undefined;
  children: ReactNode;
}

export interface PillProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, "children">,
    CommonPillProps {}

export interface PillButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">,
    CommonPillProps {}

export const Pill = forwardRef<HTMLSpanElement, PillProps>(
  ({ tone = "default", className = "", children, ...rest }, ref) => {
    const classes = [baseClasses, toneClasses[tone], className].join(" ");
    return (
      <span ref={ref} className={classes} {...rest}>
        {children}
      </span>
    );
  },
);
Pill.displayName = "Pill";

export const PillButton = forwardRef<HTMLButtonElement, PillButtonProps>(
  ({ tone = "default", className = "", type = "button", children, ...rest }, ref) => {
    const classes = [
      baseClasses,
      toneClasses[tone],
      interactiveClasses,
      interactiveToneHover[tone],
      "disabled:opacity-50 disabled:cursor-not-allowed",
      className,
    ].join(" ");
    return (
      <button ref={ref} type={type} className={classes} {...rest}>
        {children}
      </button>
    );
  },
);
PillButton.displayName = "PillButton";
