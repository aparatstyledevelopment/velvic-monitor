import { useState } from "react";
import type { Story } from "@ladle/react";

import { Toast } from "./Toast";

export default { title: "Primitives / Toast" };

export const Variants: Story = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 520 }}>
    <Toast variant="info" title="Briefing refreshed">
      Today&rsquo;s VOLV-B briefing is up to date.
    </Toast>
    <Toast variant="warning" title="Citation gap">
      One numerical claim could not be cited. The model retried but the result is shown
      anyway.
    </Toast>
    <Toast variant="negative" title="Stream interrupted">
      The connection dropped. Resending will resume from the last saved turn.
    </Toast>
  </div>
);

export const Dismissible: Story = () => {
  const [open, setOpen] = useState(true);
  if (!open) return <p className="t-small">Dismissed.</p>;
  return (
    <div style={{ maxWidth: 520 }}>
      <Toast onDismiss={() => setOpen(false)} title="Dismissible">
        Click the &times; on the right to close.
      </Toast>
    </div>
  );
};
