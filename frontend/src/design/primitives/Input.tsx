import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", ...rest }, ref) => {
    const classes = [
      "h-9 w-full px-md rounded-md",
      "bg-surface text-text-primary placeholder:text-text-tertiary",
      "border border-border",
      "focus:outline-none focus:border-text-primary",
      "transition-[border-color] duration-fast ease-standard",
      className,
    ].join(" ");
    return <input ref={ref} className={classes} {...rest} />;
  },
);
Input.displayName = "Input";
