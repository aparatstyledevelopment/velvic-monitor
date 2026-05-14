import type { Story } from "@ladle/react";

import { Avatar } from "./Avatar";

export default { title: "Primitives / Avatar" };

export const Variants: Story = () => (
  <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
    <Avatar name="Astrid Lund" email="astrid@volvo.com" />
    <Avatar name={null} email="ir@scania.com" />
    <Avatar name="Nikolas" email="n@h.com" size="sm" />
  </div>
);
