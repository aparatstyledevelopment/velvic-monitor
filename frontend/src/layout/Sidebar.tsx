import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { companiesApi } from "../api/companies";
import { Hairline } from "../design/primitives";
import { useCompanies } from "../state/companies";
import { useThreads } from "../state/threads";

import { CompanySwitcher } from "./CompanySwitcher";
import { SidebarThreadList } from "./SidebarThreadList";
import { UserMenu } from "./UserMenu";

export function Sidebar() {
  const { data: companies = [] } = useQuery({
    queryKey: ["companies"],
    queryFn: companiesApi.list,
  });
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);
  const setActiveCompanyId = useCompanies((s) => s.setActiveCompanyId);
  const setActiveThreadId = useThreads((s) => s.setActiveThreadId);

  useEffect(() => {
    if (activeCompanyId !== null) return;
    if (companies.length === 0) return;
    const primary = companies.find((c) => c.is_primary);
    setActiveCompanyId((primary ?? companies[0])?.id ?? null);
  }, [activeCompanyId, companies, setActiveCompanyId]);

  const previousCompanyId = useRef<number | null>(null);
  useEffect(() => {
    if (
      previousCompanyId.current !== null &&
      previousCompanyId.current !== activeCompanyId
    ) {
      setActiveThreadId(null);
    }
    previousCompanyId.current = activeCompanyId;
  }, [activeCompanyId, setActiveThreadId]);

  return (
    <aside
      className="hidden lg:flex w-[220px] shrink-0 flex-col border-r border-border bg-surface"
      aria-label="Primary navigation"
    >
      <div className="px-lg pt-lg pb-md">
        <span className="t-section">Velvic</span>
      </div>
      <div className="px-sm pb-md">
        <CompanySwitcher
          companies={companies}
          activeCompanyId={activeCompanyId}
          onSelect={setActiveCompanyId}
        />
      </div>
      <Hairline />
      <nav className="flex-1 py-md overflow-y-auto" aria-label="Module navigation">
        <div className="px-sm pb-md">
          <SidebarItem label="Drivers" active />
        </div>
        <SidebarThreadList />
      </nav>
      <Hairline />
      <div className="p-sm">
        <UserMenu />
      </div>
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
