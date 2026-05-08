import type { Story } from "@ladle/react";

import { TooltipProvider } from "../design/primitives";

import { ResponseCard, type ResponseCardData } from "./ResponseCard";

export default { title: "Conversation / ResponseCard" };

const base: ResponseCardData = {
  text: "",
  citation_spans: [],
  finish_reason: null,
  warning: null,
  streaming: false,
  runningTool: null,
};

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <div style={{ maxWidth: 720 }}>{children}</div>
    </TooltipProvider>
  );
}

export const Settled: Story = () => (
  <Frame>
    <ResponseCard
      data={{
        ...base,
        text: "VOLV-B is down 2.1% on the day, a 2.5pp underperformance vs OMX Stockholm PI.",
        citation_spans: [
          { start_char: 14, end_char: 18, engine_call_id: "ec_a" },
          { start_char: 30, end_char: 35, engine_call_id: "ec_b" },
        ],
        finish_reason: "stop",
      }}
    />
  </Frame>
);

export const Streaming: Story = () => (
  <Frame>
    <ResponseCard
      data={{ ...base, streaming: true, text: "Looking at today's price move…" }}
    />
  </Frame>
);

export const StreamingWithRunningTool: Story = () => (
  <Frame>
    <ResponseCard
      data={{
        ...base,
        streaming: true,
        text: "",
        runningTool: "get_price_move",
      }}
    />
  </Frame>
);

export const Refusal: Story = () => (
  <Frame>
    <ResponseCard
      data={{
        ...base,
        text: "I can only answer questions about the briefing for VOLV-B.",
        finish_reason: "refusal",
      }}
    />
  </Frame>
);

export const Warning: Story = () => (
  <Frame>
    <ResponseCard
      data={{
        ...base,
        text: "VOLV-B is down 2.1% on the day.",
        warning: "uncited_numeric",
      }}
    />
  </Frame>
);
