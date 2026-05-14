import type { Story } from "@ladle/react";

import { Card } from "./Card";
import { Pill } from "./Pill";
import { IconButton } from "./IconButton";

export default { title: "Primitives / Card" };

export const HeaderBodyFooter: Story = () => (
  <div style={{ maxWidth: 520 }}>
    <Card
      header={
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="t-section">VOLV-B price action</span>
            <Pill>9 sources</Pill>
          </div>
          <IconButton label="Share">
            <span aria-hidden="true">↗</span>
          </IconButton>
        </>
      }
      footer={<span>computed 2026-04-29 17:30 CET</span>}
    >
      <p className="t-body" style={{ color: "var(--text-secondary)" }}>
        VOLV-B closed at 247.20 SEK, down 2.1% on the session.
      </p>
    </Card>
  </div>
);

export const BodyOnly: Story = () => (
  <div style={{ maxWidth: 520 }}>
    <Card>
      <p className="t-body">A bare card with no header or footer.</p>
    </Card>
  </div>
);
