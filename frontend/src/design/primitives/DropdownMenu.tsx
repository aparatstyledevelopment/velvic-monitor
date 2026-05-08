import * as RadixDropdown from "@radix-ui/react-dropdown-menu";
import type { ReactNode } from "react";

const contentClasses = [
  "min-w-[180px] z-50",
  "rounded-md border border-border bg-surface",
  "shadow-sm",
  "p-xs",
  "data-[state=open]:animate-in data-[state=closed]:animate-out",
].join(" ");

const itemClasses = [
  "flex items-center gap-sm cursor-default select-none",
  "px-md py-xs rounded-sm",
  "t-body",
  "outline-none",
  "data-[highlighted]:bg-track",
  "data-[disabled]:opacity-50 data-[disabled]:cursor-not-allowed",
].join(" ");

const separatorClasses = "h-px my-xs bg-border";

const labelClasses = "px-md py-xs t-meta";

export const DropdownMenu = RadixDropdown.Root;
export const DropdownMenuTrigger = RadixDropdown.Trigger;
export const DropdownMenuPortal = RadixDropdown.Portal;

export function DropdownMenuContent({
  children,
  align = "start",
  sideOffset = 6,
}: {
  children: ReactNode;
  align?: "start" | "center" | "end";
  sideOffset?: number;
}) {
  return (
    <RadixDropdown.Portal>
      <RadixDropdown.Content className={contentClasses} align={align} sideOffset={sideOffset}>
        {children}
      </RadixDropdown.Content>
    </RadixDropdown.Portal>
  );
}

export function DropdownMenuItem({
  children,
  onSelect,
  disabled,
}: {
  children: ReactNode;
  onSelect?: () => void;
  disabled?: boolean;
}) {
  const props: {
    className: string;
    disabled: boolean;
    onSelect?: (e: Event) => void;
  } = {
    className: itemClasses,
    disabled: disabled ?? false,
  };
  if (onSelect !== undefined) props.onSelect = () => onSelect();
  return <RadixDropdown.Item {...props}>{children}</RadixDropdown.Item>;
}

export function DropdownMenuSeparator() {
  return <RadixDropdown.Separator className={separatorClasses} />;
}

export function DropdownMenuLabel({ children }: { children: ReactNode }) {
  return <RadixDropdown.Label className={labelClasses}>{children}</RadixDropdown.Label>;
}
