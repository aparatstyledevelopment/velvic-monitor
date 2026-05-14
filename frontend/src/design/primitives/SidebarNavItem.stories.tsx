import type { Story } from "@ladle/react";
import { LayoutDashboard, Users, Target, LineChart } from "lucide-react";

import { SidebarNavItem } from "./SidebarNavItem";

export default {
  title: "Primitives / SidebarNavItem",
};

export const States: Story = () => (
  <div style={{ width: 220, padding: 12, display: "flex", flexDirection: "column", gap: 4 }}>
    <SidebarNavItem icon={<LayoutDashboard size={14} />} label="Dashboard" active />
    <SidebarNavItem icon={<Users size={14} />} label="Shareholders" />
    <SidebarNavItem icon={<Target size={14} />} label="Targeting" soon />
    <SidebarNavItem icon={<LineChart size={14} />} label="Stock" soon />
  </div>
);
