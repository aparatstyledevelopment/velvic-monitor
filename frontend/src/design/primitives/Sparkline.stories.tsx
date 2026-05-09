import type { Story } from "@ladle/react";

import { Sparkline } from "./Sparkline";

export default {
  title: "Primitives / Sparkline",
};

const climbing = [120, 121, 119, 122, 124, 126, 124, 127, 130, 132, 131, 134, 138, 140, 139, 142];
const falling = [142, 140, 137, 138, 134, 130, 128, 126, 122, 120, 118, 119, 116, 114, 112, 110];

export const Default: Story = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 320 }}>
    <Sparkline values={climbing} />
    <Sparkline values={falling} colorVar="--signal-negative" />
    <Sparkline values={climbing} colorVar="--signal-positive" />
  </div>
);
