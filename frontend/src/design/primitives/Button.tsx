import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-surface-inverted text-surface border border-surface-inverted hover:opacity-90 active:opacity-100",
  secondary:
    "bg-surface text-text-primary border border-border hover:bg-surface-muted active:bg-track-emphasized",
  ghost:
    "bg-transparent text-text-primary border border-transparent hover:bg-surface-muted active:bg-track-emphasized",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-md text-[13px]",
  md: "h-10 px-lg text-[14px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className = "", children, ...rest }, ref) => {
    const classes = [
      "inline-flex items-center justify-center gap-sm rounded-pill",
      "font-medium",
      "transition-[background-color,opacity,border-color,color] duration-fast ease-standard",
      "focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      variants[variant],
      sizes[size],
      className,
    ].join(" ");
    return (
      <button ref={ref} className={classes} {...rest}>
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
