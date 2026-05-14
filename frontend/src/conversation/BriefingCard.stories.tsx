import type { Story } from "@ladle/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { TooltipProvider } from "../design/primitives";

import { BriefingCard } from "./BriefingCard";
import type { BriefingOut } from "../api/briefings";

export default { title: "Conversation / BriefingCard" };

const sampleBriefing: BriefingOut = {
  company_id: 1,
  module: "drivers",
  as_of_date: "2026-04-29",
  narrative:
    "VOLV-B closed at 247.20 SEK, down 2.1% on the session, against an OMX Stockholm PI return of +0.4%. The relative underperformance lines up with the morning's downward revision to FY26 truck guidance.",
  smart_chips: [
    { title: "MAR-flagged", prompt: "Any MAR-flagged items in the last 30 days?" },
    { title: "Sector lag", prompt: "Which sector peers underperformed today?" },
    { title: "Guidance revision", prompt: "Walk through the FY26 truck guidance change." },
  ],
  citation_spans: [
    { start_char: 19, end_char: 25, engine_call_id: "ec_a" },
    { start_char: 31, end_char: 35, engine_call_id: "ec_b" },
    { start_char: 96, end_char: 100, engine_call_id: "ec_c" },
  ],
  engine_call_ids: ["ec_a", "ec_b", "ec_c"],
  llm_provider: "anthropic",
  llm_model: "claude-opus-4-7",
  prompt_tokens: 1284,
  completion_tokens: 392,
  cost_cents: "0.45",
  generated_at: "2026-04-29T17:30:00Z",
};

function Frame({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient();
  return (
    <QueryClientProvider client={qc}>
      <TooltipProvider>
        <div style={{ maxWidth: 720 }}>{children}</div>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export const Populated: Story = () => (
  <Frame>
    <BriefingCard briefing={sampleBriefing} companyName="Volvo Group" />
  </Frame>
);

export const NoSmartChips: Story = () => (
  <Frame>
    <BriefingCard
      briefing={{ ...sampleBriefing, smart_chips: [] }}
      companyName="Volvo Group"
    />
  </Frame>
);

export const NoCitations: Story = () => (
  <Frame>
    <BriefingCard
      briefing={{
        ...sampleBriefing,
        citation_spans: [],
        engine_call_ids: [],
        narrative:
          "VOLV-B briefing pending — engine calls have not landed yet for this session.",
      }}
      companyName="Volvo Group"
    />
  </Frame>
);
