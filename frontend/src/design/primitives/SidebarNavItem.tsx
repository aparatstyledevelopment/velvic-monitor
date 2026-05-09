import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface SidebarNavItemProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  icon?: ReactNode;
  label: string;
  active?: boolean;
  soon?: boolean;
  trailing?: ReactNode;
}

export const SidebarNavItem = forwardRef<HTMLButtonElement, SidebarNavItemProps>(
  (
    {
      icon,
      label,
      active = false,
      soon = false,
      trailing,
      disabled,
      className = "",
      type = "button",
      ...rest
    },
    ref,
  ) => {
    const isDisabled = disabled === true || soon;
    const stateClasses = active
      ? "text-text-primary font-medium bg-surface-muted"
      : isDisabled
        ? "text-text-quaternary cursor-not-allowed"
        : "text-text-secondary hover:text-text-primary hover:bg-surface-muted";

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-current={active ? "page" : undefined}
        className={[
          "group relative flex w-full items-center gap-sm",
          "px-md h-control-lg rounded-md text-left",
          "transition-[background-color,color] duration-fast ease-standard",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
          stateClasses,
          className,
        ].join(" ")}
        {...rest}
      >
        {icon !== undefined && (
          <span
            aria-hidden="true"
            className="shrink-0 inline-flex items-center justify-center w-lg h-lg"
          >
            {icon}
          </span>
        )}
        <span className="flex-1 truncate text-md">{label}</span>
        {soon && <span className="t-meta text-text-quaternary">Soon</span>}
        {!soon && trailing !== undefined && (
          <span className="ml-auto inline-flex items-center">{trailing}</span>
        )}
      </button>
    );
  },
);
SidebarNavItem.displayName = "SidebarNavItem";
