import { beforeEach, describe, expect, it } from "vitest";

import { useArtifacts, type EngineCallEnvelope } from "../../src/state/artifacts";

const env = (id: string): EngineCallEnvelope => ({
  engine_call_id: id,
  tool_name: "get_price_move",
  module: "drivers",
  params: {},
  data: {},
  sources: [],
  status: "ok",
  latency_ms: 12,
  engine_version: "v1",
  computed_at: "2026-04-29T17:00:00Z",
});

describe("artifacts store", () => {
  beforeEach(() => {
    useArtifacts.getState().clear();
    useArtifacts.getState().closePaneMobile();
  });

  it("pushes a new envelope onto the stack", () => {
    useArtifacts.getState().push(env("ec_a"));
    expect(useArtifacts.getState().stack.map((e) => e.engine_call_id)).toEqual(["ec_a"]);
  });

  it("a second push replaces the active envelope (single-card pane)", () => {
    useArtifacts.getState().push(env("ec_a"));
    useArtifacts.getState().push(env("ec_b"));
    expect(useArtifacts.getState().stack.map((e) => e.engine_call_id)).toEqual([
      "ec_b",
    ]);
  });

  it("controls mobile pane open state", () => {
    expect(useArtifacts.getState().paneOpenMobile).toBe(false);
    useArtifacts.getState().openPaneMobile();
    expect(useArtifacts.getState().paneOpenMobile).toBe(true);
    useArtifacts.getState().closePaneMobile();
    expect(useArtifacts.getState().paneOpenMobile).toBe(false);
  });
});
