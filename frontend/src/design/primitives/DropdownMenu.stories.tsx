import type { Story } from "@ladle/react";

import { Button } from "./Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./DropdownMenu";

export default { title: "Primitives / DropdownMenu" };

export const Basic: Story = () => (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="secondary">Open menu</Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent>
      <DropdownMenuLabel>Theme</DropdownMenuLabel>
      <DropdownMenuItem>Light</DropdownMenuItem>
      <DropdownMenuItem>Dark</DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem>Sign out</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
);
