import { describe, expect, it } from "vitest";

import { chipTitle } from "../../src/conversation/chipTitle";

describe("chipTitle", () => {
  it("strips trailing punctuation", () => {
    expect(chipTitle("Top 25 holders?")).toBe("Top 25 holders");
    expect(chipTitle("Insider activity!")).toBe("Insider activity");
  });

  it("strips leading interrogatives", () => {
    expect(chipTitle("Show me top 25 holders")).toBe("Top 25 holders");
    expect(chipTitle("Tell me about peers")).toBe("About peers");
    expect(chipTitle("What is the float?")).toBe("The float");
    expect(chipTitle("Any insider activity?")).toBe("Insider activity");
    expect(chipTitle("Can you compare peers?")).toBe("Compare peers");
  });

  it("capitalises the first letter after stripping", () => {
    expect(chipTitle("show me top holders")).toBe("Top holders");
  });

  it("caps to five words with an ellipsis", () => {
    expect(chipTitle("Show me top 5 by capital share descending")).toBe(
      "Top 5 by capital share…",
    );
  });

  it("leaves short prompts intact", () => {
    expect(chipTitle("Liquidity vs peers")).toBe("Liquidity vs peers");
    expect(chipTitle("Upcoming IR events")).toBe("Upcoming IR events");
  });

  it("falls back to the original prompt when stripping leaves nothing", () => {
    expect(chipTitle("Show me")).toBe("Show me");
  });

  it("returns empty for empty input", () => {
    expect(chipTitle("")).toBe("");
    expect(chipTitle("   ")).toBe("");
  });
});
