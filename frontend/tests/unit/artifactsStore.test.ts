import { beforeEach, describe, expect, it } from "vitest";

import { useArtifacts } from "../../src/state/artifacts";

describe("artifacts store", () => {
  beforeEach(() => {
    useArtifacts.getState().clear();
    useArtifacts.getState().closePaneMobile();
  });

  it("openUncited puts a placeholder entry in the pane in single mode", () => {
    useArtifacts.getState().openUncited("2.1%");
    const state = useArtifacts.getState();
    expect(state.viewMode).toBe("single");
    expect(state.entries).toHaveLength(1);
    const entry = state.entries[0];
    expect(entry?.kind).toBe("uncited");
    if (entry?.kind === "uncited") {
      expect(entry.value).toBe("2.1%");
      expect(entry.expanded).toBe(true);
    }
  });

  it("controls mobile pane open state", () => {
    expect(useArtifacts.getState().paneOpenMobile).toBe(false);
    useArtifacts.getState().openPaneMobile();
    expect(useArtifacts.getState().paneOpenMobile).toBe(true);
    useArtifacts.getState().closePaneMobile();
    expect(useArtifacts.getState().paneOpenMobile).toBe(false);
  });

  it("clear empties entries and resets to single view", () => {
    useArtifacts.getState().openUncited("1,234.5");
    expect(useArtifacts.getState().entries).toHaveLength(1);
    useArtifacts.getState().clear();
    expect(useArtifacts.getState().entries).toEqual([]);
    expect(useArtifacts.getState().viewMode).toBe("single");
  });

  it("toggleExpanded flips the expanded flag on the matching entry", () => {
    useArtifacts.getState().openUncited("3.4%");
    const initial = useArtifacts.getState().entries[0];
    expect(initial?.expanded).toBe(true);
    if (initial !== undefined && initial.kind === "uncited") {
      useArtifacts.getState().toggleExpanded(initial.key);
    }
    expect(useArtifacts.getState().entries[0]?.expanded).toBe(false);
  });
});
