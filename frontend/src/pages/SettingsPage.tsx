import {
  Bell,
  Calendar,
  Coins,
  Globe,
  KeyRound,
  Languages,
  Maximize2,
  Palette,
  Sparkles,
  UserCog,
} from "lucide-react";
import type { ReactNode } from "react";

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

export function SettingsPage() {
  const theme = usePrefs((s) => s.theme);
  const setTheme = usePrefs((s) => s.setTheme);
  const interfaceSize = usePrefs((s) => s.interfaceSize);
  const setInterfaceSize = usePrefs((s) => s.setInterfaceSize);

  return (
    <div className="flex flex-col">
      <TakeoverHeader
        title="Settings"
        subtitle="Manage your Velvic Monitor preferences."
      />

      <div className="px-xl pb-3xl max-w-[760px] mx-auto w-full flex flex-col gap-2xl">
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
      </div>
    </div>
  );
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
        className="inline-flex items-center justify-center w-8 h-8 rounded-md bg-surface-muted text-text-secondary shrink-0"
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
              "inline-flex items-center justify-center h-7 px-md rounded-pill text-[12px] font-medium transition-colors",
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
