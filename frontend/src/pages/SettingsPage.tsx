import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  Calendar,
  Coins,
  Globe,
  KeyRound,
  Languages,
  Maximize2,
  Palette,
  ShieldOff,
  Sparkles,
  UserCog,
} from "lucide-react";
import type { ReactNode } from "react";

import { llmUsageApi, type LLMUsageSummary } from "../api/llmUsage";
import { TakeoverHeader } from "../layout/TakeoverHeader";
import { usePrefs } from "../state/prefs";
import type { InterfaceSize, Theme } from "../state/prefs";

const SIZES: { value: InterfaceSize; label: string }[] = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

const THEMES: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

const TOPIC_GATE_OPTIONS: { value: "on" | "off"; label: string }[] = [
  { value: "on", label: "On" },
  { value: "off", label: "Off" },
];

export function SettingsPage() {
  const theme = usePrefs((s) => s.theme);
  const setTheme = usePrefs((s) => s.setTheme);
  const interfaceSize = usePrefs((s) => s.interfaceSize);
  const setInterfaceSize = usePrefs((s) => s.setInterfaceSize);
  const disableTopicGate = usePrefs((s) => s.disableTopicGate);
  const setDisableTopicGate = usePrefs((s) => s.setDisableTopicGate);

  return (
    <div className="flex flex-col">
      <TakeoverHeader
        title="Settings"
        subtitle="Manage your Velvic Monitor preferences."
      />

      <div className="px-xl pb-3xl max-w-reading mx-auto w-full flex flex-col gap-2xl">
        <Section title="Display">
          <SettingRow
            icon={<Maximize2 size={16} aria-hidden="true" />}
            title="Interface size"
            description="Adjusts text and UI element sizes"
            control={
              <SegmentedControl
                value={interfaceSize}
                options={SIZES}
                onSelect={setInterfaceSize}
                ariaLabel="Interface size"
              />
            }
          />
          <SettingRow
            icon={<Palette size={16} aria-hidden="true" />}
            title="Theme"
            description="Appearance mode"
            control={
              <SegmentedControl
                value={theme}
                options={THEMES}
                onSelect={setTheme}
                ariaLabel="Theme"
              />
            }
          />
          <SettingRow
            icon={<Sparkles size={16} aria-hidden="true" />}
            title="Colorful charts"
            description="Pastel palette for briefing and report charts"
            control={<DisabledStub label="Soon" />}
          />
          <SettingRow
            icon={<Languages size={16} aria-hidden="true" />}
            title="Language"
            description="Display language"
            control={<DisabledStub label="English" />}
          />
        </Section>

        <Section title="Notifications">
          <SettingRow
            icon={<Bell size={16} aria-hidden="true" />}
            title="Email notifications"
            description="Weekly digest and alerts"
            control={<DisabledStub label="Soon" />}
          />
        </Section>

        <Section title="Security">
          <SettingRow
            icon={<KeyRound size={16} aria-hidden="true" />}
            title="Two-factor authentication"
            description="TOTP via authenticator app"
            control={<DisabledStub label="Soon" />}
          />
          <SettingRow
            icon={<UserCog size={16} aria-hidden="true" />}
            title="SSO provider"
            description="Managed by your organisation"
            control={<DisabledStub label="Soon" />}
          />
        </Section>

        <Section title="Data">
          <SettingRow
            icon={<Coins size={16} aria-hidden="true" />}
            title="Default currency"
            description="For valuation displays"
            control={<DisabledStub label="SEK" />}
          />
          <SettingRow
            icon={<Calendar size={16} aria-hidden="true" />}
            title="Date format"
            description="ISO 8601"
            control={<DisabledStub label="YYYY-MM-DD" />}
          />
          <SettingRow
            icon={<Globe size={16} aria-hidden="true" />}
            title="Time zone"
            description="Briefings are generated EOD CET"
            control={<DisabledStub label="Europe/Stockholm" />}
          />
        </Section>

        <Section title="Demo">
          <SettingRow
            icon={<ShieldOff size={16} aria-hidden="true" />}
            title="On/off-topic guardrail"
            description="Demo only. When off, every prompt reaches the model — useful for live walkthroughs that wander outside the company scope."
            control={
              <SegmentedControl
                value={disableTopicGate ? "off" : "on"}
                options={TOPIC_GATE_OPTIONS}
                onSelect={(v) => setDisableTopicGate(v === "off")}
                ariaLabel="On/off-topic guardrail"
              />
            }
          />
        </Section>

        <Section title="LLM usage">
          <UsageSummary />
        </Section>
      </div>
    </div>
  );
}

function UsageSummary() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["llm-usage-summary"],
    queryFn: () => llmUsageApi.summary(),
  });

  if (isLoading) {
    return (
      <div className="px-lg py-md t-small text-text-tertiary">
        Loading usage&hellip;
      </div>
    );
  }
  if (error !== null || data === undefined) {
    return (
      <div className="px-lg py-md t-small text-text-tertiary">
        Usage stats unavailable.
      </div>
    );
  }
  return (
    <>
      <SettingRow
        icon={<Activity size={16} aria-hidden="true" />}
        title="Total spend"
        description={`${data.total_call_count.toLocaleString()} call${
          data.total_call_count === 1 ? "" : "s"
        } · ${formatTokens(
          data.total_prompt_tokens + data.total_completion_tokens,
        )} tokens`}
        control={<UsageValue cents={data.total_cost_cents} />}
      />
      <SettingRow
        icon={<Activity size={16} aria-hidden="true" />}
        title="Last 30 days"
        description="Rolling window"
        control={<UsageValue cents={data.last_30d_cost_cents} />}
      />
      <UsageBreakdown summary={data} />
    </>
  );
}

function UsageValue({ cents }: { cents: number }) {
  return (
    <span className="t-mono text-sm tabular-nums">
      {formatCost(cents)}
    </span>
  );
}

function UsageBreakdown({ summary }: { summary: LLMUsageSummary }) {
  if (summary.by_surface.length === 0 && summary.by_model.length === 0) {
    return null;
  }
  return (
    <div className="px-lg py-md flex flex-col gap-md">
      {summary.by_surface.length > 0 && (
        <BreakdownTable
          title="By surface"
          rows={summary.by_surface.map((s) => ({
            key: s.surface,
            label: SURFACE_LABEL[s.surface] ?? s.surface,
            count: s.call_count,
            cost_cents: s.cost_cents,
          }))}
        />
      )}
      {summary.by_model.length > 0 && (
        <BreakdownTable
          title="By model"
          rows={summary.by_model.map((m) => ({
            key: m.model,
            label: m.model,
            count: m.call_count,
            cost_cents: m.cost_cents,
          }))}
        />
      )}
    </div>
  );
}

interface BreakdownRow {
  key: string;
  label: string;
  count: number;
  cost_cents: number;
}

function BreakdownTable({
  title,
  rows,
}: {
  title: string;
  rows: BreakdownRow[];
}) {
  return (
    <div className="flex flex-col gap-xs">
      <h3 className="t-meta">{title}</h3>
      <ul
        className="flex flex-col gap-xxs list-none p-0 m-0"
        aria-label={title}
      >
        {rows.map((r) => (
          <li
            key={r.key}
            className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-md"
          >
            <span className="truncate t-small">{r.label}</span>
            <span className="t-mono text-xs text-text-tertiary tabular-nums">
              {r.count.toLocaleString()}
            </span>
            <span className="t-mono text-sm tabular-nums">
              {formatCost(r.cost_cents)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const SURFACE_LABEL: Record<string, string> = {
  chat_orchestrator: "Chat (main loop)",
  chat_orchestrator_retry: "Chat (strict retry)",
  topic_gate: "Topic gate",
  thread_title: "Thread title",
  briefing_narrative: "Briefing narrative",
  briefing_narrative_retry: "Briefing retry",
  news_summary: "News summary",
};

function formatCost(cents: number): string {
  if (cents === 0) return "$0.00";
  const dollars = cents / 100;
  if (dollars < 0.01) return `$${dollars.toFixed(4)}`;
  if (dollars < 1) return `$${dollars.toFixed(3)}`;
  return `$${dollars.toFixed(2)}`;
}

function formatTokens(n: number): string {
  if (n < 1000) return n.toString();
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={`section-${title}`} className="flex flex-col">
      <h2 id={`section-${title}`} className="t-meta mb-md">
        {title}
      </h2>
      <div className="flex flex-col rounded-lg border border-border bg-surface overflow-hidden">
        {children}
      </div>
    </section>
  );
}

interface SettingRowProps {
  icon: ReactNode;
  title: string;
  description: string;
  control: ReactNode;
}

function SettingRow({ icon, title, description, control }: SettingRowProps) {
  return (
    <div className="flex items-center gap-md px-lg py-md border-b border-border last:border-b-0">
      <span
        aria-hidden="true"
        className="inline-flex items-center justify-center w-control-md h-control-md rounded-md bg-surface-muted text-text-secondary shrink-0"
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="t-label">{title}</div>
        <div className="t-small">{description}</div>
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

function SegmentedControl<T extends string>({
  value,
  options,
  onSelect,
  ariaLabel,
}: {
  value: T;
  options: SegmentedOption<T>[];
  onSelect: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="inline-flex items-center gap-xxs p-xxs rounded-pill bg-surface-muted border border-border"
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onSelect(opt.value)}
            className={[
              "inline-flex items-center justify-center h-control-sm px-md rounded-pill text-sm font-medium transition-colors",
              active
                ? "bg-surface-inverted text-surface"
                : "text-text-secondary hover:text-text-primary",
            ].join(" ")}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function DisabledStub({ label }: { label: string }) {
  return (
    <span className="t-small text-text-tertiary tracking-tight" aria-disabled="true">
      {label}
    </span>
  );
}
