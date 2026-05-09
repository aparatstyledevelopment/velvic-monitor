import { LogOut, Settings as SettingsIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { authApi } from "../api/auth";
import {
  Avatar,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../design/primitives";
import { useAuth } from "../state/auth";

export function UserMenu() {
  const me = useAuth((s) => s.me);
  const setMe = useAuth((s) => s.setMe);
  const navigate = useNavigate();

  if (me === null) return null;

  async function onLogout() {
    await authApi.logout();
    setMe(null);
    navigate("/login", { replace: true });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="User menu"
          className="flex w-full items-center gap-sm px-md py-sm rounded-md hover:bg-surface-muted focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
        >
          <Avatar name={me.display_name} email={me.email} size="sm" />
          <span className="flex-1 min-w-0 text-left">
            <span className="block t-body truncate">
              {me.display_name ?? me.email}
            </span>
            <span className="block t-meta truncate">{me.org_name}</span>
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" sideOffset={8}>
        <DropdownMenuItem onSelect={() => navigate("/settings")}>
          <span className="inline-flex items-center gap-sm">
            <SettingsIcon size={14} aria-hidden="true" />
            Settings
          </span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onLogout}>
          <span className="inline-flex items-center gap-sm">
            <LogOut size={14} aria-hidden="true" />
            Sign out
          </span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
