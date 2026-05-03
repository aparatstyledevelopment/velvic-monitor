import type { Story } from "@ladle/react";

import { Hairline } from "./Hairline";

export default {
  title: "Primitives / Hairline",
};

export const Default: Story = () => (
  <div style={{ maxWidth: 480 }}>
    <div className="t-title">Today's drivers</div>
    <Hairline />
    <p className="t-body" style={{ marginTop: 12, color: "var(--text-secondary)" }}>
      Hairlines sit between sections of an analytical card. One pixel,
      semantic --border-default, never coloured.
    </p>
  </div>
);

export const Stack: Story = () => (
  <div style={{ maxWidth: 480 }}>
    <Row label="Stock" value="VOLV-B 247.20 SEK" />
    <Hairline />
    <Row label="Daily return" value="-2.1%" />
    <Hairline />
    <Row label="Vs OMX" value="-2.5pp" />
  </div>
);

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "8px 0",
      }}
    >
      <span className="t-small" style={{ color: "var(--text-secondary)" }}>{label}</span>
      <span className="t-mono">{value}</span>
    </div>
  );
}
