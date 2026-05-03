import type { Story } from "@ladle/react";

import { Button } from "./Button";

export default {
  title: "Primitives / Button",
};

const Row = ({ children }: { children: React.ReactNode }) => (
  <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
    {children}
  </div>
);

const Stack = ({ children }: { children: React.ReactNode }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>{children}</div>
);

const Label = ({ children }: { children: React.ReactNode }) => (
  <div className="t-meta" style={{ color: "var(--text-tertiary)" }}>
    {children}
  </div>
);

export const Variants: Story = () => (
  <Stack>
    <div>
      <Label>primary</Label>
      <Row>
        <Button variant="primary">Sign in</Button>
        <Button variant="primary" disabled>Sign in</Button>
      </Row>
    </div>
    <div>
      <Label>secondary</Label>
      <Row>
        <Button variant="secondary">Cancel</Button>
        <Button variant="secondary" disabled>Cancel</Button>
      </Row>
    </div>
    <div>
      <Label>ghost</Label>
      <Row>
        <Button variant="ghost">Dismiss</Button>
        <Button variant="ghost" disabled>Dismiss</Button>
      </Row>
    </div>
  </Stack>
);

export const Sizes: Story = () => (
  <Stack>
    <div>
      <Label>small</Label>
      <Row>
        <Button size="sm">Run query</Button>
        <Button size="sm" variant="secondary">Cancel</Button>
        <Button size="sm" variant="ghost">Skip</Button>
      </Row>
    </div>
    <div>
      <Label>medium (default)</Label>
      <Row>
        <Button size="md">Run query</Button>
        <Button size="md" variant="secondary">Cancel</Button>
        <Button size="md" variant="ghost">Skip</Button>
      </Row>
    </div>
  </Stack>
);

export const FullForm: Story = () => (
  <div
    style={{
      maxWidth: 320,
      display: "flex",
      flexDirection: "column",
      gap: 12,
      padding: 16,
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-md)",
      background: "var(--surface-default)",
    }}
  >
    <div className="t-section">Confirm regenerate</div>
    <p className="t-small" style={{ color: "var(--text-secondary)" }}>
      This will overwrite the briefing for VOLV-B on 2026-04-28.
    </p>
    <Row>
      <Button variant="secondary">Cancel</Button>
      <Button>Regenerate</Button>
    </Row>
  </div>
);
