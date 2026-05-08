import * as RadixDialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

const overlayClasses = [
  "fixed inset-0 z-40",
  "bg-black/30",
  "data-[state=open]:animate-in data-[state=closed]:animate-out",
].join(" ");

const contentClasses = [
  "fixed z-50",
  "left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2",
  "w-[min(480px,calc(100vw-2rem))]",
  "rounded-lg border border-border bg-surface",
  "p-xl",
  "shadow-xl shadow-black/10",
  "focus:outline-none",
].join(" ");

export const Dialog = RadixDialog.Root;
export const DialogTrigger = RadixDialog.Trigger;
export const DialogClose = RadixDialog.Close;

export function DialogContent({
  children,
  title,
  description,
}: {
  children: ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className={overlayClasses} />
      <RadixDialog.Content className={contentClasses}>
        <RadixDialog.Title className="t-section mb-sm">{title}</RadixDialog.Title>
        {description !== undefined && (
          <RadixDialog.Description className="t-small mb-lg">
            {description}
          </RadixDialog.Description>
        )}
        {children}
      </RadixDialog.Content>
    </RadixDialog.Portal>
  );
}
