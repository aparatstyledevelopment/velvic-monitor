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

  it("dedupes by engine_call_id; second push of the same id is a no-op", () => {
    useArtifacts.getState().push(env("ec_a"));
    useArtifacts.getState().push(env("ec_a"));
    expect(useArtifacts.getState().stack).toHaveLength(1);
  });

  it("places the newest envelope on top", () => {
    useArtifacts.getState().push(env("ec_a"));
    useArtifacts.getState().push(env("ec_b"));
    expect(useArtifacts.getState().stack.map((e) => e.engine_call_id)).toEqual([
      "ec_b",
      "ec_a",
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
