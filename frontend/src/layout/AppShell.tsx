import type { ReactNode } from "react";
import { X } from "lucide-react";
import { Outlet } from "react-router-dom";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

import { ArtifactStack } from "../artifacts/ArtifactStack";
import { IconButton, TooltipProvider } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";

import { ArtifactPaneMobile } from "./ArtifactPane";
import { Sidebar } from "./Sidebar";

const RESIZE_HANDLE =
  "w-px bg-border data-[resize-handle-state=hover]:bg-border-strong data-[resize-handle-state=drag]:bg-text-primary transition-colors";

/**
 * Three-pane shell: sidebar | main | artifact stack. All splits are
 * resizable; sizes persist per device via PanelGroup `autoSaveId`. The
 * center area renders the route-level Outlet so each route picks
 * MainLayout (conversation + artifact split) or TakeoverLayout
 * (full-width).
 */
export function AppShell() {
  return (
    <TooltipProvider>
      <PanelGroup
        direction="horizontal"
        autoSaveId="velvic.shell"
        className="h-full w-full bg-surface text-text-primary"
      >
        <Panel
          id="shell-sidebar"
          order={1}
          defaultSize={18}
          minSize={14}
          maxSize={28}
          className="hidden lg:block"
        >
          <Sidebar />
        </Panel>
        <PanelResizeHandle
          id="shell-sidebar-handle"
          className={`hidden lg:block ${RESIZE_HANDLE}`}
          aria-label="Resize navigation"
        />
        <Panel id="shell-main" order={2} minSize={50}>
          <main className="h-full flex flex-col min-h-0">
            <Outlet />
          </main>
        </Panel>
      </PanelGroup>
      <ArtifactPaneMobile>
        <ArtifactStack />
      </ArtifactPaneMobile>
    </TooltipProvider>
  );
}

/**
 * Default Drivers view: a resizable split between the conversation pane
 * and the artifact stack. The TopBar lives inside `children` so it can
 * scroll with the conversation column on small heights. The artifact
 * panel collapses fully when its stack is empty AND the user has not
 * pinned it open.
 */
export function MainLayout({ children }: { children: ReactNode }) {
  const stackLength = useArtifacts((s) => s.stack.length);
  const loadingCount = useArtifacts((s) => s.loadingIds.size);
  const clear = useArtifacts((s) => s.clear);
  const showArtifact = stackLength > 0 || loadingCount > 0;
  return (
    <PanelGroup
      direction="horizontal"
      autoSaveId="velvic.main"
      className="flex-1 min-h-0"
    >
      <Panel id="main-conversation" order={1} defaultSize={68} minSize={45}>
        <div className="h-full flex flex-col min-h-0">{children}</div>
      </Panel>
      {showArtifact && (
        <>
          <PanelResizeHandle
            id="main-artifact-handle"
            className={RESIZE_HANDLE}
            aria-label="Resize artifact pane"
          />
          <Panel
            id="main-artifact"
            order={2}
            defaultSize={32}
            minSize={22}
            maxSize={48}
            className="hidden lg:block"
          >
            <aside
              className="h-full flex flex-col border-l border-border bg-surface min-h-0"
              aria-label="Artifact stack"
            >
              <header className="flex items-center justify-between gap-sm px-lg h-bar shrink-0 border-b border-border">
                <span className="t-meta">Sources</span>
                <IconButton label="Close sources" onClick={clear}>
                  <X size={14} aria-hidden="true" />
                </IconButton>
              </header>
              <div className="flex-1 overflow-y-auto scrollbar-thin px-md py-md">
                <ArtifactStack />
              </div>
            </aside>
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}

/**
 * Full-width takeover used by Settings and Drivers data-view routes.
 * Replaces both the conversation and artifact panes; back-button is the
 * caller's responsibility (rendered inside `children`).
 */
export function TakeoverLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-surface">{children}</div>
  );
}
