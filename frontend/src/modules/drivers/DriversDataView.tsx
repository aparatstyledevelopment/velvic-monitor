import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { driversApi, DRIVERS_DATA_SOURCES } from "../../api/drivers";
import { Hairline, PillButton } from "../../design/primitives";
import { TakeoverHeader } from "../../layout/TakeoverHeader";
import { useArtifacts } from "../../state/artifacts";
import { useCompanies } from "../../state/companies";

export function DriversDataView() {
  const { source } = useParams<{ source: string }>();
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);

  const definition = useMemo(
    () => DRIVERS_DATA_SOURCES.find((s) => s.key === source) ?? null,
    [source],
  );

  const dataQ = useQuery({
    queryKey: ["drivers-data", activeCompanyId, source],
    queryFn: () =>
      activeCompanyId === null || source === undefined
        ? Promise.resolve(null)
        : driversApi.data(activeCompanyId, source),
    enabled: activeCompanyId !== null && source !== undefined,
  });

  const loadById = useArtifacts((s) => s.loadById);
  const openMobile = useArtifacts((s) => s.openPaneMobile);

  async function openSource(engineCallId: string) {
    openMobile();
    await loadById(engineCallId);
  }

  if (definition === null) {
    return (
      <div className="px-xl py-2xl max-w-reading mx-auto">
        <TakeoverHeader title="Unknown source" subtitle="No such Drivers data view." />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <TakeoverHeader title={definition.label} subtitle={definition.description} />
      <div className="px-xl pb-3xl max-w-reading mx-auto w-full flex flex-col gap-lg">
        {dataQ.isLoading && (
          <p className="t-small text-text-tertiary">Loading data&hellip;</p>
        )}
        {dataQ.data !== null && dataQ.data !== undefined && (
          <>
            <div className="flex items-center gap-sm">
              <span className="t-meta">As of {dataQ.data.as_of_date}</span>
              {dataQ.data.engine_call_ids.map((id) => (
                <PillButton key={id} tone="inverse" onClick={() => openSource(id)}>
                  Source · {id.slice(0, 10)}
                </PillButton>
              ))}
            </div>
            <Hairline />
            <pre
              className="t-mono text-sm leading-relaxed whitespace-pre-wrap rounded-lg border border-border bg-surface-muted px-lg py-md overflow-x-auto"
              aria-label={`${definition.label} raw data`}
            >
              {JSON.stringify(dataQ.data.data, null, 2)}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}
