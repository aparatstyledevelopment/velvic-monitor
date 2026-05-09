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
  IconButton,
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

  const menuLabel = me.display_name ?? me.email;

  return (
    <div className="flex items-center justify-between gap-sm px-2xs">
      <IconButton label="Settings" onClick={() => navigate("/settings")}>
        <SettingsIcon size={16} aria-hidden="true" />
      </IconButton>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label={`Account menu for ${menuLabel}`}
            className="rounded-pill focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface"
          >
            <Avatar name={me.display_name} email={me.email} size="sm" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={8}>
          <div className="px-md pt-2xs pb-xs">
            <span className="block t-small text-text-primary truncate">
              {menuLabel}
            </span>
            <span className="block t-meta truncate">{me.org_name}</span>
          </div>
          <DropdownMenuSeparator />
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
    </div>
  );
}
