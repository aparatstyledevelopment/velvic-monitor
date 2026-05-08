import { beforeEach, describe, expect, it } from "vitest";

import { useThreads } from "../../src/state/threads";

describe("threads store", () => {
  beforeEach(() => {
    useThreads.getState().setActiveThreadId(null);
  });

  it("starts with no active thread", () => {
    expect(useThreads.getState().activeThreadId).toBeNull();
  });

  it("sets and clears the active thread", () => {
    useThreads.getState().setActiveThreadId("th_1");
    expect(useThreads.getState().activeThreadId).toBe("th_1");
    useThreads.getState().setActiveThreadId(null);
    expect(useThreads.getState().activeThreadId).toBeNull();
  });
});
