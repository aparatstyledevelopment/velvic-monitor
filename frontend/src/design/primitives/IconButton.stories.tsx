import type { Story } from "@ladle/react";

import { IconButton } from "./IconButton";

export default { title: "Primitives / IconButton" };

export const Variants: Story = () => (
  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
    <IconButton label="Share">↗</IconButton>
    <IconButton label="Attach">+</IconButton>
    <IconButton label="More">⋯</IconButton>
    <IconButton label="Disabled" disabled>
      ⋯
    </IconButton>
  </div>
);
