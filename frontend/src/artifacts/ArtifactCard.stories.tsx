import type { Story } from "@ladle/react";

import type { EngineCallEnvelope } from "../state/artifacts";

import { ArtifactCard } from "./ArtifactCard";

export default { title: "Artifacts / ArtifactCard" };

const sample: EngineCallEnvelope = {
  engine_call_id: "ec_8f3a3b1c4d5e",
  tool_name: "get_price_move",
  module: "drivers",
  params: { ticker: "VOLV-B", as_of_date: "2026-04-29" },
  data: {
    return_pct: -2.1,
    benchmark_return_pct: 0.4,
    relative_to_benchmark_pct: -2.5,
    close_price: 247.2,
  },
  sources: [
    {
      id: "yahoo:VOLV-B:2026-04-29",
      kind: "price_data",
      description: "Yahoo Finance EOD prices",
      url: "https://finance.yahoo.com/quote/VOLV-B.ST/history",
    },
  ],
  status: "ok",
  latency_ms: 12,
  engine_version: "v0.4.2",
  computed_at: "2026-04-29T17:30:00Z",
};

export const Populated: Story = () => (
  <div style={{ maxWidth: 440 }}>
    <ArtifactCard envelope={sample} />
  </div>
);

export const EmptyResults: Story = () => (
  <div style={{ maxWidth: 440 }}>
    <ArtifactCard envelope={{ ...sample, data: {}, sources: [] }} />
  </div>
);
