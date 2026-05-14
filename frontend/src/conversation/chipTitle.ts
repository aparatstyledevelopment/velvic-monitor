/**
 * Compress a smart-chip / follow-up question prompt down to a 1–5-word
 * label suitable for a pill. The original prompt is what gets prefilled
 * into the composer; this is just for visual real estate.
 *
 * The transform is deterministic + side-effect-free so we can swap in an
 * LLM-summarised title later without touching call sites.
 */

const LEADING_INTERROGATIVES: readonly string[] = [
  "show me ",
  "tell me ",
  "what's ",
  "what is ",
  "what are ",
  "what ",
  "why ",
  "how ",
  "who's ",
  "who has ",
  "who ",
  "any ",
  "can you ",
  "could you ",
  "are there ",
  "is there ",
  "do we ",
  "do you ",
  "give me ",
  "list ",
  "find ",
  "compare ",
];

const MAX_WORDS = 5;
const HARD_CHAR_CAP = 32;

export function chipTitle(prompt: string, maxWords = MAX_WORDS): string {
  const trimmed = prompt.trim();
  if (trimmed.length === 0) return "";

  // Drop trailing punctuation.
  let body = trimmed.replace(/[?.!,;:]+$/g, "").trim();

  // Strip a single leading interrogative phrase, if present.
  const lower = body.toLowerCase();
  for (const lead of LEADING_INTERROGATIVES) {
    if (lower.startsWith(lead)) {
      body = body.slice(lead.length);
      break;
    }
  }
  body = body.trim();
  if (body.length === 0) {
    body = trimmed.replace(/[?.!,;:]+$/g, "").trim();
  }

  // Capitalize first letter.
  body = body.charAt(0).toUpperCase() + body.slice(1);

  // Trim to N words.
  const words = body.split(/\s+/);
  if (words.length > maxWords) {
    body = words.slice(0, maxWords).join(" ") + "…";
  }

  // Hard char cap as a safety net for unusually long single tokens.
  if (body.length > HARD_CHAR_CAP) {
    body = body.slice(0, HARD_CHAR_CAP - 1).trimEnd() + "…";
  }

  return body;
}
