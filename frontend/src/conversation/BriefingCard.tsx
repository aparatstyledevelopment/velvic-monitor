import type { ReactNode } from "react";
import { useState } from "react";

import type { BriefingOut } from "../api/briefings";
import { Card, IconButton, Pill } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { engineCallsApi } from "../api/engineCalls";

import { renderWithCitations } from "./citationRenderer";

interface BriefingCardProps {
  briefing: BriefingOut;
  companyName: string;
}

export function BriefingCard({ briefing, companyName }: BriefingCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const push = useArtifacts((s) => s.push);
  const openMobile = useArtifacts((s) => s.openPaneMobile);

  async function onCite(engineCallId: string) {
    const envelope = await engineCallsApi.get(engineCallId);
    push(envelope);
    openMobile();
  }

  const header = (
    <BriefingHeader
      companyName={companyName}
      asOfDate={briefing.as_of_date}
      sourceCount={briefing.engine_call_ids.length}
      collapsed={collapsed}
      onToggle={() => setCollapsed((c) => !c)}
    />
  );

  return (
    <Card header={header}>
      {!collapsed && (
        <div className="flex flex-col gap-md">
          <p className="t-body whitespace-pre-wrap">
            {renderWithCitations({
              text: briefing.narrative,
              spans: briefing.citation_spans,
              onCite,
            })}
          </p>
          {briefing.smart_chips.length > 0 && (
            <div className="flex flex-wrap gap-xs">
              {briefing.smart_chips.map((chip, i) => (
                <Pill key={i}>{chip}</Pill>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

interface BriefingHeaderProps {
  companyName: string;
  asOfDate: string;
  sourceCount: number;
  collapsed: boolean;
  onToggle: () => void;
}

function BriefingHeader({
  companyName,
  asOfDate,
  sourceCount,
  collapsed,
  onToggle,
}: BriefingHeaderProps): ReactNode {
  return (
    <>
      <div className="flex items-center gap-sm min-w-0">
        <span className="t-section truncate">{companyName} · Drivers · {asOfDate}</span>
        <Pill>{sourceCount} sources</Pill>
      </div>
      <IconButton
        label={collapsed ? "Expand briefing" : "Collapse briefing"}
        onClick={onToggle}
      >
        <span aria-hidden="true">{collapsed ? "▾" : "▴"}</span>
      </IconButton>
    </>
  );
}
