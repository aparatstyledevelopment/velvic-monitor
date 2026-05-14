import type { Story } from "@ladle/react";

import { Stat } from "./Stat";

export default {
  title: "Primitives / Stat",
};

export const Default: Story = () => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, maxWidth: 760 }}>
    <Stat label="Capital" value="2.87%" delta="unchanged 30d" />
    <Stat label="Votes" value="2.50%" delta="unchanged 30d" />
    <Stat label="Shares" value="880,456" meta="of 30,677,919" />
    <Stat label="Market value" value="14M" meta="SEK" />
  </div>
);

export const TonedDeltas: Story = () => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, maxWidth: 600 }}>
    <Stat label="Today" value="247.20" delta="+5.07%" tone="positive" />
    <Stat label="vs OMXSPI" value="+4.6pp" tone="positive" />
    <Stat label="vs Sector" value="-1.3pp" tone="negative" />
  </div>
);
