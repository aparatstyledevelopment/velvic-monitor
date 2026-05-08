import type { CompletionEvent } from "./streamingTypes";

export async function* parseSSEStream(
  response: Response,
): AsyncGenerator<CompletionEvent, void, void> {
  if (!response.ok) {
    throw new Error(`stream request failed: ${response.status}`);
  }
  if (response.body === null) {
    throw new Error("stream response had no body");
  }
  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (value) {
        buffer += value;
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const ev = parseChunk(chunk);
          if (ev !== null) yield ev;
          boundary = buffer.indexOf("\n\n");
        }
      }
      if (done) break;
    }
    if (buffer.trim().length > 0) {
      const tail = parseChunk(buffer);
      if (tail !== null) yield tail;
    }
  } finally {
    reader.releaseLock();
  }
}

export function parseChunk(chunk: string): CompletionEvent | null {
  for (const rawLine of chunk.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (!line.startsWith("data: ")) continue;
    const payload = line.slice(6);
    if (payload.length === 0) continue;
    try {
      return JSON.parse(payload) as CompletionEvent;
    } catch {
      return null;
    }
  }
  return null;
}
