import type { ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

import { ArtifactStack } from "../artifacts/ArtifactStack";
import { TooltipProvider } from "../design/primitives";

import { ArtifactPaneMobile } from "./ArtifactPane";
import { Sidebar } from "./Sidebar";

/**
 * Three-pane shell: sidebar | main | artifact stack. The sidebar is fixed
 * on the left; the main and artifact panels are resizable via
 * react-resizable-panels (sizes persist per device via the autoSaveId).
 *
 * The center area is filled by route-level Outlets so each route can
 * choose whether to render the conversation + artifact split (default
 * Drivers view) or a full-width takeover (Settings, Drivers data views).
 */
export function AppShell() {
  return (
    <TooltipProvider>
      <div className="flex h-full w-full bg-surface text-text-primary">
        <Sidebar />
        <main className="flex-1 min-w-0 flex flex-col min-h-0">
          <Outlet />
        </main>
        <ArtifactPaneMobile>
          <ArtifactStack />
        </ArtifactPaneMobile>
      </div>
    </TooltipProvider>
  );
}

/**
 * Default Drivers view: a resizable split between the conversation pane
 * and the artifact stack. The TopBar lives inside `children` so it can
 * scroll with the conversation column on small heights.
 */
export function MainLayout({ children }: { children: ReactNode }) {
  return (
    <PanelGroup
      direction="horizontal"
      autoSaveId="velvic.main"
      className="flex-1 min-h-0"
    >
      <Panel defaultSize={68} minSize={45}>
        <div className="h-full flex flex-col min-h-0">{children}</div>
      </Panel>
      <PanelResizeHandle
        className="w-px bg-border data-[resize-handle-state=hover]:bg-border-strong data-[resize-handle-state=drag]:bg-text-primary transition-colors"
        aria-label="Resize artifact pane"
      />
      <Panel defaultSize={32} minSize={22} maxSize={48} className="hidden lg:block">
        <aside
          className="h-full flex flex-col border-l border-border bg-surface min-h-0"
          aria-label="Artifact stack"
        >
          <header className="px-lg h-bar flex items-center shrink-0 border-b border-border">
            <span className="t-meta">Sources</span>
          </header>
          <div className="flex-1 overflow-y-auto px-md py-md">
            <ArtifactStack />
          </div>
        </aside>
      </Panel>
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
