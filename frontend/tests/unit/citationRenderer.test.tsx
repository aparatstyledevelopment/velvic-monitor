import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  resolveSpans,
  renderWithCitations,
  type CitationSpan,
} from "../../src/conversation/citationRenderer";
import { TooltipProvider } from "../../src/design/primitives";

const span = (start: number, end: number, id: string): CitationSpan => ({
  start_char: start,
  end_char: end,
  engine_call_id: id,
});

describe("resolveSpans", () => {
  it("assigns stable 1-based ordinals per distinct engine_call_id", () => {
    const text = "The price was 247.20 SEK, down 2.1% on the day.";
    const spans = [
      span(14, 24, "ec_a"),
      span(32, 36, "ec_b"),
    ];
    const out = resolveSpans(text, spans);
    expect(out.map((s) => s.ordinal)).toEqual([1, 2]);
  });

  it("reuses the same ordinal when an id repeats further down the text", () => {
    const text = "247.20 SEK, then 246.10 SEK, then 245.20 SEK.";
    const spans = [
      span(0, 10, "ec_a"),
      span(17, 27, "ec_b"),
      span(34, 44, "ec_a"),
    ];
    const out = resolveSpans(text, spans);
    expect(out.map((s) => s.engineCallId)).toEqual(["ec_a", "ec_b", "ec_a"]);
    expect(out.map((s) => s.ordinal)).toEqual([1, 2, 1]);
  });

  it("drops malformed spans where end <= start or out of range", () => {
    const text = "abc";
    const spans = [span(0, 0, "x"), span(1, 0, "y"), span(0, 100, "z")];
    expect(resolveSpans(text, spans)).toEqual([]);
  });

  it("sorts unsorted spans before assigning ordinals", () => {
    const text = "abcdefghijkl";
    const spans = [span(8, 10, "b"), span(0, 2, "a")];
    const out = resolveSpans(text, spans);
    expect(out.map((s) => s.start)).toEqual([0, 8]);
    expect(out.map((s) => s.ordinal)).toEqual([1, 2]);
  });
});

describe("renderWithCitations", () => {
  function H({
    text,
    spans,
    onCite,
  }: {
    text: string;
    spans: CitationSpan[];
    onCite: (id: string) => void;
  }) {
    return (
      <TooltipProvider>
        <p>{renderWithCitations({ text, spans, onCite })}</p>
      </TooltipProvider>
    );
  }

  it("renders one chip per distinct engine call", () => {
    render(
      <H
        text="A is 1.0 and B is 2.0."
        spans={[span(5, 8, "ec_a"), span(18, 21, "ec_b")]}
        onCite={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(2);
    expect(screen.getByLabelText("Open evidence 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Open evidence 2")).toBeInTheDocument();
  });

  it("collapses consecutive same-id citations into a single chip", () => {
    const text = "value-1value-2";
    const spans = [span(0, 7, "ec_a"), span(7, 14, "ec_a")];
    render(<H text={text} spans={spans} onCite={vi.fn()} />);
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("invokes the onCite handler with the engine_call_id when a chip is clicked", () => {
    const onCite = vi.fn();
    render(
      <H text="hello 1.0 world" spans={[span(6, 9, "ec_42")]} onCite={onCite} />,
    );
    fireEvent.click(screen.getByLabelText("Open evidence 1"));
    expect(onCite).toHaveBeenCalledWith("ec_42");
  });
});
