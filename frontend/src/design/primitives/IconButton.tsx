import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  children: ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ label, className = "", children, ...rest }, ref) => {
    const classes = [
      "inline-flex items-center justify-center",
      "h-control-sm w-control-sm rounded-md",
      "text-text-secondary hover:text-text-primary hover:bg-track",
      "transition-[background-color,color] duration-fast ease-standard",
      "focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      className,
    ].join(" ");
    return (
      <button
        ref={ref}
        type="button"
        aria-label={label}
        title={label}
        className={classes}
        {...rest}
      >
        {children}
      </button>
    );
  },
);
IconButton.displayName = "IconButton";
