import { ChevronDown, ChevronUp } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { BriefingOut } from "../api/briefings";
import { Card, PillButton } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { useComposer } from "../state/composer";

import { chipTitle } from "./chipTitle";
import { renderWithCitations } from "./citationRenderer";

interface BriefingCardProps {
  briefing: BriefingOut;
  companyName: string;
}

export function BriefingCard({ briefing, companyName }: BriefingCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const loadById = useArtifacts((s) => s.loadById);
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const setDraft = useComposer((s) => s.setDraft);

  async function onCite(engineCallId: string) {
    openMobile();
    await loadById(engineCallId);
  }

  async function openPrimarySource() {
    const id = briefing.engine_call_ids[0];
    if (id === undefined) return;
    await onCite(id);
  }

  const title = formatBriefingTitle(briefing.as_of_date);

  const header = (
    <BriefingHeader
      title={title}
      asOfDate={briefing.as_of_date}
      hasSource={briefing.engine_call_ids.length > 0}
      collapsed={collapsed}
      onToggle={() => setCollapsed((c) => !c)}
      onOpenSource={openPrimarySource}
    />
  );

  void companyName;

  return (
    <Card header={header}>
      {!collapsed && (
        <div className="flex flex-col gap-lg">
          <p className="t-body whitespace-pre-wrap">
            {renderWithCitations({
              text: briefing.narrative,
              spans: briefing.citation_spans,
              onCite,
            })}
          </p>

          {briefing.smart_chips.length > 0 && (
            <div className="flex flex-wrap gap-xs pt-xs">
              {briefing.smart_chips.map((chip, i) => (
                <PillButton
                  key={i}
                  onClick={() => setDraft(chip)}
                  aria-label={`Use suggestion: ${chip}`}
                  title={chip}
                >
                  {chipTitle(chip)}
                </PillButton>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

interface BriefingHeaderProps {
  title: string;
  asOfDate: string;
  hasSource: boolean;
  collapsed: boolean;
  onToggle: () => void;
  onOpenSource: () => void;
}

function BriefingHeader({
  title,
  asOfDate,
  hasSource,
  collapsed,
  onToggle,
  onOpenSource,
}: BriefingHeaderProps): ReactNode {
  return (
    <>
      <div className="flex flex-col min-w-0 gap-xxs">
        <span className="t-section truncate">{title}</span>
        <span className="t-meta">Generated · {asOfDate}</span>
      </div>
      <div className="flex items-center gap-sm shrink-0">
        {hasSource && (
          <PillButton tone="inverse" onClick={onOpenSource}>
            Source
          </PillButton>
        )}
        <PillButton onClick={onToggle} aria-expanded={!collapsed}>
          {collapsed ? (
            <>
              <ChevronDown size={12} aria-hidden="true" />
              Expand
            </>
          ) : (
            <>
              <ChevronUp size={12} aria-hidden="true" />
              Collapse
            </>
          )}
        </PillButton>
      </div>
    </>
  );
}

function formatBriefingTitle(asOfDateStr: string): string {
  const parsed = new Date(asOfDateStr + "T00:00:00Z");
  if (Number.isNaN(parsed.getTime())) return "Morning Briefing";
  const weekday = parsed.toLocaleDateString("en-US", {
    weekday: "long",
    timeZone: "UTC",
  });
  return `${weekday} Morning Briefing`;
}
