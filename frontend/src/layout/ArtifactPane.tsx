import type { ReactNode } from "react";

import { Hairline, IconButton } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { useHistoryBridge } from "../history/bridge";

export function ArtifactPane({ children }: { children?: ReactNode }) {
  return (
    <aside
      className="hidden lg:flex w-[400px] xl:w-[440px] shrink-0 flex-col border-l border-border bg-surface"
      aria-label="Artifact stack"
    >
      <header className="px-lg py-md flex items-center justify-between">
        <span className="t-section">Sources</span>
      </header>
      <Hairline />
      <div className="flex-1 overflow-y-auto px-md py-md">{children}</div>
    </aside>
  );
}

export function ArtifactPaneMobile({ children }: { children?: ReactNode }) {
  const open = useArtifacts((s) => s.paneOpenMobile);
  const close = useArtifacts((s) => s.closePaneMobile);
  useHistoryBridge(open, close);

  if (!open) return null;
  return (
    <div className="lg:hidden fixed inset-0 z-30 flex">
      <button
        type="button"
        aria-label="Close source pane"
        className="absolute inset-0 bg-black/30"
        onClick={close}
      />
      <aside
        className="ml-auto h-full w-[88vw] max-w-[420px] flex flex-col bg-surface border-l border-border"
        role="dialog"
        aria-label="Artifact stack"
      >
        <header className="px-lg py-md flex items-center justify-between">
          <span className="t-section">Sources</span>
          <IconButton label="Close" onClick={close}>
            <span aria-hidden="true">×</span>
          </IconButton>
        </header>
        <Hairline />
        <div className="flex-1 overflow-y-auto px-md py-md">{children}</div>
      </aside>
    </div>
  );
}

