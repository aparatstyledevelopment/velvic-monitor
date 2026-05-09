import type { ReactNode } from "react";

interface CodeBlockProps {
  /** Heading is the wrapper aria-label; the visual heading lives outside. */
  ariaLabel?: string;
  children: ReactNode;
}

export function CodeBlock({ ariaLabel, children }: CodeBlockProps) {
  return (
    <pre
      aria-label={ariaLabel}
      className="t-mono text-sm leading-relaxed whitespace-pre-wrap rounded-md border border-border bg-surface-inverted text-surface px-lg py-md overflow-x-auto"
    >
      {children}
    </pre>
  );
}
