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

type SmartChip = BriefingOut["smart_chips"][number];

export function BriefingCard({ briefing, companyName }: BriefingCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const openSingle = useArtifacts((s) => s.openSingle);
  const openList = useArtifacts((s) => s.openList);
  const openUncited = useArtifacts((s) => s.openUncited);
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const setDraft = useComposer((s) => s.setDraft);

  async function onCite(engineCallId: string) {
    openMobile();
    await openSingle(engineCallId);
  }

  function onUncited(value: string) {
    openMobile();
    openUncited(value);
  }

  async function openAllSources() {
    const ids = briefing.engine_call_ids;
    if (ids.length === 0) return;
    openMobile();
    await openList(ids);
  }

  const title = formatBriefingTitle(briefing.as_of_date);
  const preview = previewSentences(briefing.narrative, 2);

  const header = (
    <BriefingHeader
      title={title}
      asOfDate={briefing.as_of_date}
      hasSource={briefing.engine_call_ids.length > 0}
      sourceCount={briefing.engine_call_ids.length}
      collapsed={collapsed}
      onToggle={() => setCollapsed((c) => !c)}
      onOpenSources={openAllSources}
    />
  );

  void companyName;

  return (
    <Card header={header}>
      {collapsed && preview.length > 0 && (
        <p className="t-body text-text-secondary">{preview}</p>
      )}
      {!collapsed && (
        <div className="flex flex-col gap-lg">
          <p className="t-body whitespace-pre-wrap">
            {renderWithCitations({
              text: briefing.narrative,
              spans: briefing.citation_spans,
              onCite,
              onUncited,
            })}
          </p>

          {briefing.smart_chips.length > 0 && (
            <div className="flex flex-wrap gap-xs pt-xs">
              {briefing.smart_chips.map((chip, i) => {
                const { label, prompt } = resolveChip(chip);
                return (
                  <PillButton
                    key={i}
                    onClick={() => setDraft(prompt)}
                    aria-label={`Use suggestion: ${prompt}`}
                    title={prompt}
                  >
                    {label}
                  </PillButton>
                );
              })}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

/**
 * Smart chips were originally `list[str]` (the raw prompt). Phase-3
 * moved them to `{title, prompt}`. Legacy briefing rows still hold
 * strings until they're regenerated — fall back to deriving a label
 * from the prompt in that case.
 */
function resolveChip(chip: SmartChip | string): { label: string; prompt: string } {
  if (typeof chip === "string") {
    return { label: chipTitle(chip), prompt: chip };
  }
  const prompt = chip.prompt;
  const label = chip.title.trim() || chipTitle(prompt);
  return { label, prompt };
}

function previewSentences(text: string, count: number): string {
  const trimmed = text.trim();
  if (trimmed.length === 0) return "";
  const matches = trimmed.match(/[^.!?]+[.!?]+/g);
  if (matches === null || matches.length === 0) {
    return trimmed.length > 200
      ? `${trimmed.slice(0, 199).trimEnd()}…`
      : trimmed;
  }
  return matches.slice(0, count).join(" ").trim();
}

interface BriefingHeaderProps {
  title: string;
  asOfDate: string;
  hasSource: boolean;
  sourceCount: number;
  collapsed: boolean;
  onToggle: () => void;
  onOpenSources: () => void;
}

function BriefingHeader({
  title,
  asOfDate,
  hasSource,
  sourceCount,
  collapsed,
  onToggle,
  onOpenSources,
}: BriefingHeaderProps): ReactNode {
  return (
    <>
      <div className="flex flex-col min-w-0 gap-xxs">
        <span className="t-section truncate">{title}</span>
        <span className="t-meta">Generated · {asOfDate}</span>
      </div>
      <div className="flex items-center gap-sm shrink-0">
        {hasSource && (
          <PillButton
            tone="inverse"
            onClick={onOpenSources}
            aria-label={`Open ${sourceCount} source${sourceCount === 1 ? "" : "s"}`}
          >
            {sourceCount > 1 ? `Sources · ${sourceCount}` : "Source"}
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
