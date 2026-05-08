import { useQuery, useQueryClient } from "@tanstack/react-query";

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
        className="flex items-center gap-sm mx-md mb-xs px-md py-sm rounded-md t-body text-text-secondary hover:bg-track text-left"
      >
        <span aria-hidden="true">+</span>
        <span>New conversation</span>
      </button>
      <div className="px-md pt-lg pb-xs t-meta">Conversations</div>
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
    "group relative flex items-center gap-sm mx-md px-md py-sm rounded-md",
    active ? "bg-track text-text-primary" : "text-text-secondary hover:bg-track",
  ].join(" ");
  return (
    <li>
      <div className={rowCls}>
        <button
          type="button"
          onClick={onSelect}
          className="flex-1 min-w-0 text-left"
          aria-current={active ? "page" : undefined}
        >
          <span className="block t-body truncate">{thread.title}</span>
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
