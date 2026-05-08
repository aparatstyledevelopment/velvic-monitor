import * as RadixTooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

const contentClasses = [
  "rounded-sm bg-surface-inverted text-surface px-sm py-xs",
  "text-[12px] leading-tight",
  "shadow-md shadow-black/15",
  "select-none",
].join(" ");

export function TooltipProvider({ children }: { children: ReactNode }) {
  return <RadixTooltip.Provider delayDuration={200}>{children}</RadixTooltip.Provider>;
}

export function Tooltip({
  children,
  label,
  side = "top",
}: {
  children: ReactNode;
  label: string;
  side?: "top" | "bottom" | "left" | "right";
}) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content className={contentClasses} side={side} sideOffset={4}>
          {label}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
