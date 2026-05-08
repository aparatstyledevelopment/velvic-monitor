import { useNavigate } from "react-router-dom";

import { authApi } from "../api/auth";
import {
  Avatar,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../design/primitives";
import { useAuth } from "../state/auth";
import { usePrefs } from "../state/prefs";
import type { InterfaceSize, Theme } from "../state/prefs";

const THEMES: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

const SIZES: { value: InterfaceSize; label: string }[] = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

export function UserMenu() {
  const me = useAuth((s) => s.me);
  const setMe = useAuth((s) => s.setMe);
  const theme = usePrefs((s) => s.theme);
  const setTheme = usePrefs((s) => s.setTheme);
  const interfaceSize = usePrefs((s) => s.interfaceSize);
  const setInterfaceSize = usePrefs((s) => s.setInterfaceSize);
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
          className="flex w-full items-center gap-sm px-md py-sm rounded-md hover:bg-track focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
        >
          <Avatar name={me.display_name} email={me.email} size="sm" />
          <span className="flex-1 min-w-0 text-left">
            <span className="block t-body truncate">{me.display_name ?? me.email}</span>
            <span className="block t-meta truncate">{me.org_name}</span>
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" sideOffset={8}>
        <DropdownMenuLabel>Theme</DropdownMenuLabel>
        {THEMES.map((t) => (
          <DropdownMenuItem key={t.value} onSelect={() => setTheme(t.value)}>
            <span className="flex items-center justify-between w-full gap-md">
              <span>{t.label}</span>
              {theme === t.value && (
                <span aria-hidden="true" className="text-text-tertiary">
                  ✓
                </span>
              )}
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Interface size</DropdownMenuLabel>
        {SIZES.map((s) => (
          <DropdownMenuItem
            key={s.value}
            onSelect={() => setInterfaceSize(s.value)}
          >
            <span className="flex items-center justify-between w-full gap-md">
              <span>{s.label}</span>
              {interfaceSize === s.value && (
                <span aria-hidden="true" className="text-text-tertiary">
                  ✓
                </span>
              )}
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onLogout}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
