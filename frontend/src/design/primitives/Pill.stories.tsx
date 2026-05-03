import type { Story } from "@ladle/react";

import { Pill } from "./Pill";

export default {
  title: "Primitives / Pill",
};

export const Variants: Story = () => (
  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
    <Pill>v0.1 · phase-0</Pill>
    <Pill>regulatory</Pill>
    <Pill>MAR-flagged</Pill>
    <Pill>cached</Pill>
    <Pill>OMX Stockholm PI</Pill>
  </div>
);

export const InContext: Story = () => (
  <div
    style={{
      maxWidth: 480,
      padding: 16,
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-md)",
      background: "var(--surface-default)",
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div className="t-title">Drivers</div>
      <Pill>Phase 0 placeholder</Pill>
    </div>
    <p className="t-body" style={{ color: "var(--text-secondary)", marginTop: 12 }}>
      Pills sit alongside titles, source markers, and module chips. They are
      decorative chrome — never tappable on the briefing card itself.
    </p>
  </div>
);
