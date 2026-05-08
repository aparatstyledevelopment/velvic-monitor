import type { Story } from "@ladle/react";

import { IconButton } from "./IconButton";
import { Tooltip, TooltipProvider } from "./Tooltip";

export default { title: "Primitives / Tooltip" };

export const Basic: Story = () => (
  <TooltipProvider>
    <Tooltip label="Open evidence">
      <IconButton label="Open evidence">↗</IconButton>
    </Tooltip>
  </TooltipProvider>
);
