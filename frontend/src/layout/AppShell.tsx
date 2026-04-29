import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full w-full bg-surface text-text-primary">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col">{children}</main>
    </div>
  );
}

function Sidebar() {
  return (
    <aside
      className="hidden md:flex w-[220px] shrink-0 flex-col border-r border-border bg-surface"
      aria-label="Primary navigation"
    >
      <div className="px-lg py-lg">
        <span className="t-section">Velvic</span>
      </div>
      <nav className="flex-1 px-md py-sm">
        <SidebarItem label="Drivers" active />
      </nav>
      <div className="px-lg py-md t-meta">v0.1 · phase-0</div>
    </aside>
  );
}

function SidebarItem({ label, active = false }: { label: string; active?: boolean }) {
  const cls = [
    "block w-full text-left px-md py-sm rounded-md t-body",
    active ? "bg-track text-text-primary" : "text-text-secondary hover:bg-track",
  ].join(" ");
  return (
    <button type="button" className={cls}>
      {label}
    </button>
  );
}
