import { useQuery } from "@tanstack/react-query";

import { companiesApi } from "../../api/companies";
import { ConversationPane } from "../../conversation/ConversationPane";
import { MainLayout } from "../../layout/AppShell";
import { TopBar } from "../../layout/TopBar";
import { useCompanies } from "../../state/companies";

import { QuickActionsPanel } from "./QuickActionsPanel";

export function DriversModule() {
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: companiesApi.list,
  });
  const company = companies.data?.find((c) => c.id === activeCompanyId);

  return (
    <>
      <TopBar />
      <MainLayout>
        {activeCompanyId === null || company === undefined ? (
          <div className="flex-1 min-w-0 flex items-center justify-center">
            <p className="t-small text-text-tertiary">
              Select a company in the sidebar to load its briefing.
            </p>
          </div>
        ) : (
          <ConversationPane companyId={company.id} companyName={company.name} />
        )}
      </MainLayout>
      <QuickActionsPanel />
    </>
  );
}
