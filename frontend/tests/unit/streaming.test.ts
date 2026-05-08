import { describe, expect, it } from "vitest";

import { parseChunk, parseSSEStream } from "../../src/conversation/streaming";

function toResponse(...chunks: string[]): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

async function collect<T>(iter: AsyncIterable<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const v of iter) out.push(v);
  return out;
}

describe("parseChunk", () => {
  it("parses a single data: line into a typed event", () => {
    const ev = parseChunk('data: {"type":"text_delta","text":"hi"}');
    expect(ev).toEqual({ type: "text_delta", text: "hi" });
  });

  it("returns null for malformed JSON", () => {
    expect(parseChunk("data: not-json")).toBeNull();
  });

  it("returns null when no data: prefix is present", () => {
    expect(parseChunk(": heartbeat\nretry: 1000")).toBeNull();
  });

  it("strips trailing \\r from CRLF-delimited streams", () => {
    const ev = parseChunk('data: {"type":"text_delta","text":"hi"}\r');
    expect(ev).toEqual({ type: "text_delta", text: "hi" });
  });
});

describe("parseSSEStream", () => {
  it("yields events in order across multiple chunks", async () => {
    const r = toResponse(
      'data: {"type":"text_delta","text":"hello"}\n\n',
      'data: {"type":"text_delta","text":" world"}\n\n',
      'data: {"type":"done","turn_id":"t1","thread_id":"th1","finish_reason":"stop","prompt_tokens":1,"completion_tokens":2,"cost_cents":0,"model":"m","provider":"p","engine_call_ids":[]}\n\n',
    );
    const events = await collect(parseSSEStream(r));
    expect(events.map((e) => e.type)).toEqual(["text_delta", "text_delta", "done"]);
  });

  it("handles event boundaries split across two chunks", async () => {
    const r = toResponse(
      'data: {"type":"text_delta","text":"hel',
      'lo"}\n\n',
    );
    const events = await collect(parseSSEStream(r));
    expect(events).toEqual([{ type: "text_delta", text: "hello" }]);
  });

  it("ignores unparseable lines and continues", async () => {
    const r = toResponse(
      'data: garbage\n\n',
      'data: {"type":"text_delta","text":"ok"}\n\n',
    );
    const events = await collect(parseSSEStream(r));
    expect(events).toEqual([{ type: "text_delta", text: "ok" }]);
  });

  it("throws on non-2xx responses", async () => {
    const r = new Response("nope", { status: 500 });
    await expect(collect(parseSSEStream(r))).rejects.toThrow(/500/);
  });
});
