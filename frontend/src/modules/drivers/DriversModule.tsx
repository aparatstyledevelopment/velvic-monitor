import { useQuery } from "@tanstack/react-query";

import { briefingsApi } from "../../api/briefings";
import { companiesApi } from "../../api/companies";
import { ApiError } from "../../api/client";
import { BriefingCard } from "../../conversation/BriefingCard";
import { useArtifacts } from "../../state/artifacts";
import { useCompanies } from "../../state/companies";
import { Toast } from "../../design/primitives";
import { IconButton } from "../../design/primitives";

export function DriversModule() {
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);
  const openMobile = useArtifacts((s) => s.openPaneMobile);

  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: companiesApi.list,
  });
  const company = companies.data?.find((c) => c.id === activeCompanyId);

  const briefing = useQuery({
    queryKey: ["briefing", "latest", activeCompanyId],
    queryFn: () => briefingsApi.latest(activeCompanyId as number),
    enabled: activeCompanyId !== null,
  });

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <header className="lg:hidden flex items-center justify-between px-lg py-md border-b border-border">
        <h1 className="t-section">Drivers</h1>
        <IconButton label="Open sources" onClick={openMobile}>
          <span aria-hidden="true">↗</span>
        </IconButton>
      </header>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[720px] w-full px-lg py-xl flex flex-col gap-lg">
          {activeCompanyId === null && (
            <p className="t-small text-text-tertiary">
              Select a company in the sidebar to load its briefing.
            </p>
          )}
          {briefing.isLoading && (
            <p className="t-small text-text-tertiary">Loading briefing&hellip;</p>
          )}
          {briefing.isError && <BriefingError error={briefing.error} />}
          {briefing.data !== undefined && company !== undefined && (
            <BriefingCard briefing={briefing.data} companyName={company.name} />
          )}
        </div>
      </div>
    </div>
  );
}

function BriefingError({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.code === "no_briefing") {
    return (
      <Toast title="No briefing yet">
        Today&rsquo;s briefing has not generated yet. Check back after the EOD pipeline
        completes.
      </Toast>
    );
  }
  return (
    <Toast variant="negative" title="Briefing unavailable">
      We couldn&rsquo;t load the briefing for this company. Try refreshing the page.
    </Toast>
  );
}
