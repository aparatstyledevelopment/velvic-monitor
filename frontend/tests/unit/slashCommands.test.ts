import { describe, expect, it } from "vitest";

import {
  autocompleteCandidates,
  parseInput,
} from "../../src/conversation/slashCommands";

describe("parseInput", () => {
  it("returns the trimmed text for plain messages", () => {
    expect(parseInput("  why did volv-b move?  ")).toEqual({
      kind: "message",
      text: "why did volv-b move?",
    });
  });

  it("recognises /new with no args", () => {
    expect(parseInput("/new")).toEqual({ kind: "slash", command: "new", args: "" });
  });

  it("recognises /help with no args", () => {
    expect(parseInput("/help")).toEqual({
      kind: "slash",
      command: "help",
      args: "",
    });
  });

  it("treats unknown /commands as plain messages", () => {
    expect(parseInput("/wat")).toEqual({ kind: "message", text: "/wat" });
  });

  it("treats /clear as a plain message (not implemented in v1)", () => {
    expect(parseInput("/clear")).toEqual({ kind: "message", text: "/clear" });
  });
});

describe("autocompleteCandidates", () => {
  it("returns both commands when input is bare /", () => {
    expect(autocompleteCandidates("/").map((c) => c.name)).toEqual(["new", "help"]);
  });

  it("filters by prefix", () => {
    expect(autocompleteCandidates("/n").map((c) => c.name)).toEqual(["new"]);
    expect(autocompleteCandidates("/he").map((c) => c.name)).toEqual(["help"]);
  });

  it("returns nothing once a space is typed", () => {
    expect(autocompleteCandidates("/new ")).toEqual([]);
  });

  it("returns nothing for plain text", () => {
    expect(autocompleteCandidates("hello")).toEqual([]);
  });
});
