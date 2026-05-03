import { useState } from "react";
import type { Story } from "@ladle/react";

import { Input } from "./Input";

export default {
  title: "Primitives / Input",
};

const Field = ({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) => (
  <label style={{ display: "flex", flexDirection: "column", gap: 4, maxWidth: 360 }}>
    <span className="t-meta">{label}</span>
    {children}
    {hint ? <span className="t-small" style={{ color: "var(--text-tertiary)" }}>{hint}</span> : null}
  </label>
);

export const Default: Story = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <Field label="Email">
      <Input type="email" placeholder="you@company.com" />
    </Field>
    <Field label="Password" hint="12 characters minimum.">
      <Input type="password" />
    </Field>
  </div>
);

export const Filled: Story = () => {
  const [value, setValue] = useState("Volvo Investor Relations");
  return (
    <Field label="Organisation name">
      <Input value={value} onChange={(e) => setValue(e.target.value)} />
    </Field>
  );
};

export const Disabled: Story = () => (
  <Field label="Locked field">
    <Input disabled value="Cannot edit" readOnly />
  </Field>
);
