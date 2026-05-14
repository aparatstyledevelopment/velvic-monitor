import type { Story } from "@ladle/react";
import { ChevronUp } from "lucide-react";

import { Pill, PillButton } from "./Pill";

export default {
  title: "Primitives / Pill",
};

export const StaticTones: Story = () => (
  <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
    <Pill>3 sources</Pill>
    <Pill tone="muted">Insider</Pill>
    <Pill tone="inverse">Source</Pill>
  </div>
);

export const InteractivePillButtons: Story = () => (
  <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
    <PillButton>Show me top 25 holders</PillButton>
    <PillButton tone="inverse">Source</PillButton>
    <PillButton tone="muted">Liquidity vs peers</PillButton>
    <PillButton>
      <ChevronUp size={12} />
      Collapse
    </PillButton>
    <PillButton disabled>Disabled</PillButton>
  </div>
);

export const InContext: Story = () => (
  <div
    style={{
      maxWidth: 480,
      padding: 16,
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-lg)",
      background: "var(--surface-default)",
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div className="t-section">Saturday Morning Briefing</div>
      <PillButton tone="inverse">Source</PillButton>
    </div>
    <p className="t-body" style={{ color: "var(--text-secondary)", marginTop: 12 }}>
      The black <code>tone="inverse"</code> pill mirrors the &ldquo;Source&rdquo; chip in the
      design blueprint. Inline pills tag editorial sections.
    </p>
  </div>
);
