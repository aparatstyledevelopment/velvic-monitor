import {
  ArrowDownUp,
  ArrowLeftRight,
  ChartLine,
  ClipboardList,
  Eye,
  FileText,
  LayoutDashboard,
  Mail,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  Users,
  type LucideIcon,
} from "lucide-react";

/**
 * Module manifest. Phase-3 v1 ships only `drivers`; the others are
 * declared here so the sidebar can advertise the full product surface
 * to users (each rendered with a `Soon` chip and disabled).
 *
 * Routes are indicative — when a module ships, its `route` is what the
 * SidebarNavItem links to. `enabled: false` means the navigation item
 * is disabled and the route is not registered yet.
 */
export interface ModuleSpec {
  key: string;
  label: string;
  icon: LucideIcon;
  route: string;
  enabled: boolean;
  /** Extra path prefixes that should also mark this module active. */
  activePrefixes?: readonly string[];
}

export const MODULES: readonly ModuleSpec[] = [
  {
    key: "drivers",
    label: "Drivers",
    icon: Sparkles,
    route: "/",
    enabled: true,
    activePrefixes: ["/drivers"],
  },
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, route: "/dashboard", enabled: false },
  { key: "shareholders", label: "Shareholders", icon: Users, route: "/shareholders", enabled: false },
  { key: "targeting", label: "Targeting", icon: Target, route: "/targeting", enabled: false },
  { key: "stock", label: "Stock", icon: ChartLine, route: "/stock", enabled: false },
  { key: "liquidity", label: "Liquidity", icon: ArrowLeftRight, route: "/liquidity", enabled: false },
  { key: "insider", label: "Insider", icon: Eye, route: "/insider", enabled: false },
  { key: "short", label: "Short", icon: TrendingDown, route: "/short", enabled: false },
  { key: "governance", label: "Governance", icon: ShieldCheck, route: "/governance", enabled: false },
  { key: "crm", label: "CRM", icon: Mail, route: "/crm", enabled: false },
  { key: "estimates", label: "Estimates", icon: ArrowDownUp, route: "/estimates", enabled: false },
  { key: "reports", label: "Reports", icon: FileText, route: "/reports", enabled: false },
  { key: "ir-events", label: "IR events", icon: ClipboardList, route: "/ir-events", enabled: false },
  { key: "filings", label: "Filings", icon: ScrollText, route: "/filings", enabled: false },
] as const;
