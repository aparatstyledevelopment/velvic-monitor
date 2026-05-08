export type CompletionEvent =
  | { type: "text_delta"; text: string }
  | {
      type: "tool_call";
      id: string;
      name: string;
      arguments: Record<string, unknown>;
    }
  | {
      type: "tool_result";
      tool_call_id: string;
      engine_call_id?: string;
      tool_name?: string;
      error?: string;
    }
  | { type: "warning"; code: string; message: string }
  | {
      type: "done";
      turn_id: string;
      thread_id: string;
      finish_reason: string;
      prompt_tokens: number;
      completion_tokens: number;
      cost_cents: number;
      model: string;
      provider: string;
      engine_call_ids: string[];
    }
  | { type: "error"; message: string };
