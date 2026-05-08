import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResponseCard, type ResponseCardData } from "../../src/conversation/ResponseCard";
import { TooltipProvider } from "../../src/design/primitives";

function H({ data }: { data: ResponseCardData }) {
  return (
    <TooltipProvider>
      <ResponseCard data={data} />
    </TooltipProvider>
  );
}

const base: ResponseCardData = {
  text: "",
  citation_spans: [],
  finish_reason: null,
  warning: null,
  streaming: false,
  runningTool: null,
};

describe("ResponseCard", () => {
  it("renders a thinking indicator when streaming and no text yet", () => {
    render(<H data={{ ...base, streaming: true }} />);
    expect(screen.getByText(/thinking/i)).toBeInTheDocument();
  });

  it("renders the running tool pill while a tool_call is in flight", () => {
    render(
      <H data={{ ...base, streaming: true, text: "Looking…", runningTool: "get_price_move" }} />,
    );
    expect(screen.getByText(/engine: get_price_move/i)).toBeInTheDocument();
  });

  it("renders refusal chrome when finish_reason is refusal", () => {
    render(
      <H
        data={{
          ...base,
          text: "I can only answer questions about the briefing for VOLV-B.",
          finish_reason: "refusal",
        }}
      />,
    );
    expect(screen.getByText("Off-topic")).toBeInTheDocument();
  });

  it("renders a friendly explanation for uncited_numeric warnings", () => {
    render(
      <H
        data={{ ...base, text: "VOLV-B is down 2.1%.", warning: "uncited_numeric" }}
      />,
    );
    expect(
      screen.getByText(/could not be cited/i),
    ).toBeInTheDocument();
  });

  it("renders an arbitrary warning string verbatim", () => {
    render(<H data={{ ...base, text: "Hi.", warning: "Stream interrupted." }} />);
    expect(screen.getByText("Stream interrupted.")).toBeInTheDocument();
  });

  it("renders a citation chip when spans are present", () => {
    render(
      <H
        data={{
          ...base,
          text: "Down 2.1%.",
          citation_spans: [
            { start_char: 5, end_char: 9, engine_call_id: "ec_a" },
          ],
        }}
      />,
    );
    expect(screen.getByLabelText("Open evidence 1")).toBeInTheDocument();
  });
});
