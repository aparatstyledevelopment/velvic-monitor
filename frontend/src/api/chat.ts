import { api } from "./client";
import type { components } from "@shared/openapi/types";

export type ChatThreadOut = components["schemas"]["ChatThreadOut"];
export type ChatThreadDetail = components["schemas"]["ChatThreadDetail"];
export type ChatTurnOut = components["schemas"]["ChatTurnOut"];

export const chatApi = {
  list: () => api<ChatThreadOut[]>("/chat/threads"),
  get: (threadId: string) => api<ChatThreadDetail>(`/chat/threads/${threadId}`),
  create: (companyId: number, title?: string) =>
    api<ChatThreadOut>("/chat/threads", {
      method: "POST",
      body: title === undefined ? { company_id: companyId } : {
        company_id: companyId,
        title,
      },
    }),
  archive: (threadId: string) =>
    api<void>(`/chat/threads/${threadId}`, { method: "DELETE" }),
  postTurn: (threadId: string, message: string) =>
    fetch(`/api/chat/threads/${threadId}/turns`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message }),
    }),
};
