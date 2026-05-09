import { useQuery } from "@tanstack/react-query";
import { LayoutGrid } from "lucide-react";
import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { companiesApi } from "../api/companies";
import { Hairline, IconButton, SidebarNavItem } from "../design/primitives";
import { useCompanies } from "../state/companies";
import { useQuickActions } from "../state/quickActions";
import { useThreads } from "../state/threads";

import { CompanySwitcher } from "./CompanySwitcher";
import { MODULES } from "./modules";
import { SidebarThreadList } from "./SidebarThreadList";
import { UserMenu } from "./UserMenu";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const toggleQuickActions = useQuickActions((s) => s.toggle);

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
      <div className="px-lg pt-lg pb-2xs">
        <span className="t-section">Velvic Monitor</span>
        <span className="t-meta block mt-xs">Monitor</span>
      </div>
      <div className="px-sm pb-md pt-md">
        <CompanySwitcher
          companies={companies}
          activeCompanyId={activeCompanyId}
          onSelect={setActiveCompanyId}
        />
      </div>
      <Hairline />
      <nav
        className="flex-1 px-sm pt-md pb-md overflow-y-auto flex flex-col gap-xxs"
        aria-label="Modules"
      >
        {MODULES.map((m) => {
          const isActive =
            m.enabled &&
            (m.route === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(m.route));
          const trailing =
            m.enabled && isActive ? (
              <IconButton
                label="Open quick actions"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleQuickActions();
                }}
              >
                <LayoutGrid size={14} aria-hidden="true" />
              </IconButton>
            ) : undefined;
          return (
            <SidebarNavItem
              key={m.key}
              icon={<m.icon size={14} />}
              label={m.label}
              active={isActive}
              soon={!m.enabled}
              trailing={trailing}
              onClick={() => {
                if (m.enabled) navigate(m.route);
              }}
            />
          );
        })}
        <div className="mt-md">
          <SidebarThreadList />
        </div>
      </nav>
      <Hairline />
      <div className="p-sm">
        <UserMenu />
      </div>
    </aside>
  );
}
