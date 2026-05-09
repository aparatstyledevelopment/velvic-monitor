import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { briefingsApi, type BriefingOut } from "../api/briefings";
import { chatApi, type ChatTurnOut } from "../api/chat";
import { engineCallsApi } from "../api/engineCalls";
import { ApiError } from "../api/client";
import {
  Dialog,
  DialogClose,
  DialogContent,
  IconButton,
  Toast,
} from "../design/primitives";
import { Button } from "../design/primitives";
import { useArtifacts } from "../state/artifacts";
import { useCompanies } from "../state/companies";
import { useThreads } from "../state/threads";

import { BriefingCard } from "./BriefingCard";
import { Composer } from "./Composer";
import {
  ResponseCard,
  responseCardFromTurn,
  type ResponseCardData,
} from "./ResponseCard";
import { SLASH_REGISTRY, type ParsedInput } from "./slashCommands";
import { parseSSEStream } from "./streaming";
import { UserCard } from "./UserCard";

interface ConversationPaneProps {
  companyId: number;
  companyName: string;
}

export function ConversationPane({ companyId, companyName }: ConversationPaneProps) {
  const queryClient = useQueryClient();
  const activeThreadId = useThreads((s) => s.activeThreadId);
  const setActiveThreadId = useThreads((s) => s.setActiveThreadId);
  const setActiveCompanyId = useCompanies((s) => s.setActiveCompanyId);
  const pushArtifact = useArtifacts((s) => s.push);
  const openMobile = useArtifacts((s) => s.openPaneMobile);

  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [streaming, setStreaming] = useState<ResponseCardData | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  const briefingQ = useQuery({
    queryKey: ["briefing", "latest", companyId],
    queryFn: () => briefingsApi.latest(companyId),
  });

  const threadQ = useQuery({
    queryKey: ["thread", activeThreadId],
    queryFn: () =>
      activeThreadId === null
        ? Promise.resolve(null)
        : chatApi.get(activeThreadId),
    enabled: activeThreadId !== null,
  });

  async function handleSubmit(parsed: ParsedInput) {
    if (parsed.kind === "slash") {
      if (parsed.command === "help") setHelpOpen(true);
      if (parsed.command === "new") {
        setActiveThreadId(null);
        setStreaming(null);
        setPendingUser(null);
        await queryClient.invalidateQueries({ queryKey: ["thread"] });
      }
      return;
    }
    await sendMessage(parsed.text);
  }

  async function sendMessage(text: string) {
    let threadId = activeThreadId;
    if (threadId === null) {
      const created = await chatApi.create(companyId);
      threadId = created.id;
      setActiveThreadId(threadId);
      await queryClient.invalidateQueries({ queryKey: ["threads"] });
    }
    setPendingUser(text);
    setStreaming({
      text: "",
      citation_spans: [],
      finish_reason: null,
      warning: null,
      streaming: true,
      runningTool: null,
      suggested_followups: [],
    });
    try {
      const response = await chatApi.postTurn(threadId, text);
      let buffer = "";
      const seenEngineCallIds = new Set<string>();
      const inflightTools = new Map<string, string>();
      for await (const ev of parseSSEStream(response)) {
        if (ev.type === "text_delta") {
          buffer += ev.text;
          setStreaming((prev) =>
            prev === null ? prev : { ...prev, text: buffer },
          );
        } else if (ev.type === "tool_call") {
          inflightTools.set(ev.id, ev.name);
          setStreaming((prev) =>
            prev === null ? prev : { ...prev, runningTool: ev.name },
          );
        } else if (ev.type === "tool_result") {
          inflightTools.delete(ev.tool_call_id);
          const remaining = inflightTools.values().next();
          setStreaming((prev) =>
            prev === null
              ? prev
              : {
                  ...prev,
                  runningTool: remaining.done ? null : remaining.value,
                },
          );
          if (
            ev.engine_call_id !== undefined &&
            !seenEngineCallIds.has(ev.engine_call_id)
          ) {
            seenEngineCallIds.add(ev.engine_call_id);
            const envelope = await engineCallsApi.get(ev.engine_call_id);
            pushArtifact(envelope);
          }
        } else if (ev.type === "warning") {
          setStreaming((prev) =>
            prev === null ? prev : { ...prev, warning: ev.message },
          );
        } else if (ev.type === "done") {
          setStreaming((prev) =>
            prev === null
              ? prev
              : {
                  ...prev,
                  streaming: false,
                  finish_reason: ev.finish_reason,
                  suggested_followups: ev.suggested_followups ?? [],
                },
          );
        } else if (ev.type === "error") {
          setStreaming((prev) =>
            prev === null
              ? prev
              : {
                  ...prev,
                  streaming: false,
                  finish_reason: "error",
                  warning: ev.message,
                },
          );
        }
      }
    } finally {
      await queryClient.invalidateQueries({ queryKey: ["thread", threadId] });
      await queryClient.invalidateQueries({ queryKey: ["threads"] });
      setPendingUser(null);
      setStreaming(null);
    }
  }

  // Avoid the unused warning for setActiveCompanyId — wired here for slice 5
  // when the sidebar can swap companies and clear the active thread together.
  void setActiveCompanyId;

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <header className="lg:hidden flex items-center justify-between px-lg py-md border-b border-border">
        <h1 className="t-section">Drivers</h1>
        <IconButton label="Open sources" onClick={openMobile}>
          <span aria-hidden="true">↗</span>
        </IconButton>
      </header>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[760px] w-full px-xl py-2xl flex flex-col gap-xl">
          <BriefingSection
            briefing={briefingQ.data}
            companyName={companyName}
            isLoading={briefingQ.isLoading}
            error={briefingQ.error}
          />
          {(threadQ.data?.turns ?? [])
            .filter((t: ChatTurnOut) => t.role === "user" || t.role === "assistant")
            .map((t: ChatTurnOut) =>
              t.role === "user" ? (
                <UserCard key={t.id} text={t.content} />
              ) : (
                <ResponseCard key={t.id} data={responseCardFromTurn(t)} />
              ),
            )}
          {pendingUser !== null && <UserCard text={pendingUser} />}
          {streaming !== null && <ResponseCard data={streaming} />}
        </div>
      </div>
      <Composer disabled={streaming !== null} onSubmit={handleSubmit} />
      <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
        <DialogContent
          title="Slash commands"
          description="Two commands are supported in this build."
        >
          <ul className="t-body flex flex-col gap-sm" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {SLASH_REGISTRY.map((c) => (
              <li key={c.name} className="flex items-baseline gap-md">
                <code className="t-mono text-[13px]">{c.label}</code>
                <span className="t-small text-text-secondary">{c.description}</span>
              </li>
            ))}
          </ul>
          <div className="flex justify-end mt-lg">
            <DialogClose asChild>
              <Button>Close</Button>
            </DialogClose>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function BriefingSection({
  briefing,
  companyName,
  isLoading,
  error,
}: {
  briefing: BriefingOut | undefined;
  companyName: string;
  isLoading: boolean;
  error: unknown;
}) {
  if (isLoading) {
    return <p className="t-small text-text-tertiary">Loading briefing&hellip;</p>;
  }
  if (error instanceof ApiError && error.code === "no_briefing") {
    return (
      <Toast title="No briefing yet">
        Today&rsquo;s briefing has not generated yet. Check back after the EOD pipeline
        completes.
      </Toast>
    );
  }
  if (error !== null && error !== undefined) {
    return (
      <Toast variant="negative" title="Briefing unavailable">
        We couldn&rsquo;t load the briefing for this company. Try refreshing the page.
      </Toast>
    );
  }
  if (briefing === undefined) return null;
  return <BriefingCard briefing={briefing} companyName={companyName} />;
}
