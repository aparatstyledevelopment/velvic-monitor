import { useQuery } from "@tanstack/react-query";

import { companiesApi } from "../../api/companies";
import { ConversationPane } from "../../conversation/ConversationPane";
import { useCompanies } from "../../state/companies";

export function DriversModule() {
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: companiesApi.list,
  });
  const company = companies.data?.find((c) => c.id === activeCompanyId);

  if (activeCompanyId === null || company === undefined) {
    return (
      <div className="flex-1 min-w-0 flex items-center justify-center">
        <p className="t-small text-text-tertiary">
          Select a company in the sidebar to load its briefing.
        </p>
      </div>
    );
  }

  return <ConversationPane companyId={company.id} companyName={company.name} />;
}
