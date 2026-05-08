import type { ReactNode } from "react";

import { ArtifactStack } from "../artifacts/ArtifactStack";
import { TooltipProvider } from "../design/primitives";

import { ArtifactPane, ArtifactPaneMobile } from "./ArtifactPane";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider>
      <div className="flex h-full w-full bg-surface text-text-primary">
        <Sidebar />
        <main className="flex-1 min-w-0 flex flex-col">{children}</main>
        <ArtifactPane>
          <ArtifactStack />
        </ArtifactPane>
        <ArtifactPaneMobile>
          <ArtifactStack />
        </ArtifactPaneMobile>
      </div>
    </TooltipProvider>
  );
}
