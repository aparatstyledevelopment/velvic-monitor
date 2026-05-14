import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { briefingsApi, type BriefingOut } from "../api/briefings";
import { chatApi, type ChatTurnOut } from "../api/chat";
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
import { useComposer } from "../state/composer";
import { usePrefs } from "../state/prefs";
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
  const openMobile = useArtifacts((s) => s.openPaneMobile);
  const disableTopicGate = usePrefs((s) => s.disableTopicGate);

  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [streaming, setStreaming] = useState<ResponseCardData | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const restoreDraft = useComposer((s) => s.setDraft);

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
    setSendError(null);
    let threadId = activeThreadId;
    if (threadId === null) {
      try {
        const created = await chatApi.create(companyId, deriveThreadTitle(text));
        threadId = created.id;
        setActiveThreadId(threadId);
        await queryClient.invalidateQueries({ queryKey: ["threads"] });
      } catch (err) {
        // Couldn't even create the thread — restore the draft so the
        // user isn't silently stranded with their text gone.
        restoreDraft(text);
        setSendError(describeNetworkError(err));
        return;
      }
    }
    setPendingUser(text);
    setStreaming({
      text: "",
      citation_spans: [],
      finish_reason: null,
      warning: null,
      streaming: true,
      runningTool: null,
      toolEvents: [],
      suggested_followups: [],
    });
    try {
      const response = await chatApi.postTurn(threadId, text, {
        bypassTopicGate: disableTopicGate,
      });
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
            prev === null
              ? prev
              : {
                  ...prev,
                  runningTool: ev.name,
                  toolEvents: [
                    ...prev.toolEvents,
                    { id: ev.id, name: ev.name, status: "pending" },
                  ],
                },
          );
        } else if (ev.type === "tool_result") {
          inflightTools.delete(ev.tool_call_id);
          const remaining = inflightTools.values().next();
          const isErr = ev.engine_call_id === undefined;
          setStreaming((prev) =>
            prev === null
              ? prev
              : {
                  ...prev,
                  runningTool: remaining.done ? null : remaining.value,
                  toolEvents: prev.toolEvents.map((t) =>
                    t.id === ev.tool_call_id
                      ? { ...t, status: isErr ? "error" : "done" }
                      : t,
                  ),
                },
          );
          if (ev.engine_call_id !== undefined) {
            seenEngineCallIds.add(ev.engine_call_id);
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
    } catch (err) {
      // Most commonly: TypeError "Failed to fetch" when the network drops
      // mid-stream, or the dev proxy hiccups. The backend may or may not
      // have persisted the user turn — invalidating the thread query in
      // `finally` lets the refresh tell us; meanwhile restore the draft
      // so the user isn't left with their message vanished.
      restoreDraft(text);
      setSendError(describeNetworkError(err));
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
    <div className="flex-1 min-w-0 min-h-0 flex flex-col">
      <header className="lg:hidden flex items-center justify-between px-lg py-md border-b border-border">
        <h1 className="t-section">Drivers</h1>
        <IconButton label="Open sources" onClick={openMobile}>
          <span aria-hidden="true">↗</span>
        </IconButton>
      </header>
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-reading w-full px-xl py-2xl flex flex-col gap-xl">
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
          {sendError !== null && (
            <Toast variant="negative" title="Couldn't send message">
              {sendError} Your text has been restored to the composer.
            </Toast>
          )}
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
                <code className="t-mono text-md">{c.label}</code>
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

/**
 * Title for the auto-created thread on the user's first message. We use
 * the message itself (collapsed whitespace, capped) so the sidebar shows
 * something distinct per conversation instead of the
 * "Conversation about $TICKER" backend default.
 */
function deriveThreadTitle(text: string, maxLen = 60): string {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length === 0) return "New conversation";
  if (cleaned.length <= maxLen) return cleaned;
  return `${cleaned.slice(0, maxLen - 1).trimEnd()}…`;
}

function describeNetworkError(err: unknown): string {
  if (err instanceof TypeError) return "The server is unreachable.";
  if (err instanceof Error) return err.message;
  return "Unknown error.";
}
