export type SlashCommand = "new" | "help";

export interface SlashRegistryEntry {
  name: SlashCommand;
  label: string;
  description: string;
}

export const SLASH_REGISTRY: SlashRegistryEntry[] = [
  { name: "new", label: "/new", description: "Start a new conversation" },
  { name: "help", label: "/help", description: "Show the slash command list" },
];

export interface ParsedSlash {
  kind: "slash";
  command: SlashCommand;
  args: string;
}

export interface ParsedMessage {
  kind: "message";
  text: string;
}

export type ParsedInput = ParsedSlash | ParsedMessage;

export function parseInput(raw: string): ParsedInput {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("/")) return { kind: "message", text: trimmed };
  const match = trimmed.match(/^\/([a-zA-Z]+)(?:\s+(.*))?$/);
  if (match === null) return { kind: "message", text: trimmed };
  const command = match[1] as SlashCommand;
  const args = match[2] ?? "";
  if (command !== "new" && command !== "help") {
    return { kind: "message", text: trimmed };
  }
  return { kind: "slash", command, args };
}

const AUTOCOMPLETE_RE = /^\/([a-zA-Z]*)$/;

export function autocompleteCandidates(raw: string): SlashRegistryEntry[] {
  const m = raw.match(AUTOCOMPLETE_RE);
  if (m === null) return [];
  const prefix = (m[1] ?? "").toLowerCase();
  return SLASH_REGISTRY.filter((c) => c.name.startsWith(prefix));
}
