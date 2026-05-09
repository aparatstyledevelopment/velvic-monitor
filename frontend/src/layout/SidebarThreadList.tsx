import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { chatApi, type ChatThreadOut } from "../api/chat";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  IconButton,
} from "../design/primitives";
import { useCompanies } from "../state/companies";
import { useThreads } from "../state/threads";

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
      <button
        type="button"
        onClick={() => setActiveThreadId(null)}
        className="flex items-center gap-sm mx-md mb-sm px-md py-sm rounded-md t-body text-text-secondary hover:bg-surface-muted text-left"
      >
        <Plus size={14} aria-hidden="true" />
        <span>New conversation</span>
      </button>
      <div className="px-md pt-md pb-xs t-meta">Recent chats</div>
      {threads.isLoading && (
        <p className="px-md t-small text-text-tertiary">Loading&hellip;</p>
      )}
      {!threads.isLoading && inScope.length === 0 && (
        <p className="px-md t-small text-text-tertiary">No conversations yet.</p>
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
  const rowCls = [
    "group relative flex items-start gap-sm mx-md px-md py-sm rounded-md",
    active
      ? "bg-surface-muted text-text-primary"
      : "text-text-secondary hover:bg-surface-muted",
  ].join(" ");
  return (
    <li>
      <div className={rowCls}>
        <button
          type="button"
          onClick={onSelect}
          className="flex-1 min-w-0 text-left flex flex-col gap-xxs"
          aria-current={active ? "page" : undefined}
        >
          <span className="block t-body truncate leading-snug">{thread.title}</span>
          <span className="flex items-center gap-xs t-meta normal-case tracking-normal text-[11px] text-text-tertiary">
            <span className="truncate">Drivers</span>
            <span aria-hidden="true">·</span>
            <span className="shrink-0">{relativeTime(thread.updated_at)}</span>
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
