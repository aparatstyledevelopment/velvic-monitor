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
    "bg-surface-inverted text-surface border border-surface-inverted hover:opacity-90",
  secondary:
    "bg-surface text-text-primary border border-border hover:bg-track",
  ghost: "bg-transparent text-text-primary hover:bg-track",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-md text-[13px] rounded-md",
  md: "h-9 px-lg text-[14px] rounded-md",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className = "", children, ...rest }, ref) => {
    const classes = [
      "inline-flex items-center justify-center gap-sm",
      "transition-[background-color,opacity,border-color] duration-fast ease-standard",
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
