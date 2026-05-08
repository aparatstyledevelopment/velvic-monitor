import type { Story } from "@ladle/react";

import { Button } from "./Button";
import { Dialog, DialogClose, DialogContent, DialogTrigger } from "./Dialog";

export default { title: "Primitives / Dialog" };

export const Basic: Story = () => (
  <Dialog>
    <DialogTrigger asChild>
      <Button variant="secondary">Open dialog</Button>
    </DialogTrigger>
    <DialogContent
      title="Slash commands"
      description="Three commands are supported in this build."
    >
      <ul className="t-body" style={{ listStyle: "none", padding: 0, margin: 0 }}>
        <li>
          <code className="t-mono">/new</code> &mdash; start a new conversation in the current
          company
        </li>
        <li>
          <code className="t-mono">/help</code> &mdash; this dialog
        </li>
      </ul>
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
        <DialogClose asChild>
          <Button>Close</Button>
        </DialogClose>
      </div>
    </DialogContent>
  </Dialog>
);
