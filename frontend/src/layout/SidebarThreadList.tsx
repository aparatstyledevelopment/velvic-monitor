import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";

import { chatApi, type ChatThreadOut } from "../api/chat";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Hairline,
  IconButton,
} from "../design/primitives";
import { useCompanies } from "../state/companies";
import { useThreads } from "../state/threads";

import { MODULES } from "./modules";

export function SidebarThreadList() {
  const queryClient = useQueryClient();
  const activeCompanyId = useCompanies((s) => s.activeCompanyId);
  const activeThreadId = useThreads((s) => s.activeThreadId);
  const setActiveThreadId = useThreads((s) => s.setActiveThreadId);

  const threads = useQuery({
    queryKey: ["threads"],
    queryFn: chatApi.list,
  });

  const inScope = (threads.data ?? []).filter(
    (t) => activeCompanyId === null || t.company_id === activeCompanyId,
  );

  async function archive(thread: ChatThreadOut) {
    if (activeThreadId === thread.id) setActiveThreadId(null);
    await chatApi.archive(thread.id);
    await queryClient.invalidateQueries({ queryKey: ["threads"] });
  }

  return (
    <div className="flex flex-col">
      <Hairline className="mx-sm mb-md" />
      <div className="px-md pb-2xs t-meta">Recent chats</div>
      {threads.isLoading && (
        <p className="px-md py-xs t-small text-text-tertiary">Loading&hellip;</p>
      )}
      {!threads.isLoading && inScope.length === 0 && (
        <p className="px-md py-xs t-small text-text-tertiary">No conversations yet.</p>
      )}
      <ul className="flex flex-col list-none p-0 m-0">
        {inScope.map((t) => (
          <ThreadRow
            key={t.id}
            thread={t}
            active={t.id === activeThreadId}
            onSelect={() => setActiveThreadId(t.id)}
            onArchive={() => archive(t)}
          />
        ))}
      </ul>
    </div>
  );
}

const ACTIVE_MODULE_LABEL =
  MODULES.find((m) => m.enabled)?.label ?? "Drivers";

function ThreadRow({
  thread,
  active,
  onSelect,
  onArchive,
}: {
  thread: ChatThreadOut;
  active: boolean;
  onSelect: () => void;
  onArchive: () => void;
}) {
  return (
    <li className="relative">
      {active && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-2xs bottom-2xs w-px bg-text-primary"
        />
      )}
      <div className="group relative flex items-center gap-sm pl-md pr-2xs">
        <button
          type="button"
          onClick={onSelect}
          aria-current={active ? "page" : undefined}
          className="flex-1 min-w-0 flex items-center gap-sm py-2xs text-left rounded-md focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
        >
          <MessageSquare
            size={14}
            aria-hidden="true"
            className={["shrink-0", active ? "text-text-primary" : "text-text-tertiary"].join(" ")}
          />
          <span className="flex-1 min-w-0 flex flex-col">
            <span
              className={[
                "truncate text-sm",
                active ? "text-text-primary font-medium" : "text-text-secondary",
              ].join(" ")}
            >
              {thread.title}
            </span>
            <span className="t-meta normal-case tracking-normal text-xs text-text-tertiary truncate">
              {ACTIVE_MODULE_LABEL}
            </span>
          </span>
          <span className="t-meta normal-case tracking-normal text-xs text-text-tertiary shrink-0">
            {relativeTime(thread.updated_at)}
          </span>
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <IconButton
              label="Thread actions"
              className="opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100 focus:opacity-100"
            >
              <span aria-hidden="true">⋯</span>
            </IconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onArchive}>Archive</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}

const MINUTE = 60;
const HOUR = MINUTE * 60;
const DAY = HOUR * 24;

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = Math.max(0, (Date.now() - t) / 1000);
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)}m`;
  if (diff < DAY) return `${Math.floor(diff / HOUR)}h`;
  if (diff < DAY * 7) return `${Math.floor(diff / DAY)}d`;
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
