import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Avatar } from "../../src/design/primitives/Avatar";

describe("Avatar", () => {
  it("derives initials from a two-word name", () => {
    render(<Avatar name="Astrid Lund" email="astrid@volvo.com" />);
    expect(screen.getByText("AL")).toBeInTheDocument();
  });

  it("uses first initial when only a single word is given", () => {
    render(<Avatar name="Astrid" email="astrid@volvo.com" />);
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("falls back to first letter of email when name is null", () => {
    render(<Avatar name={null} email="ir@scania.com" />);
    expect(screen.getByText("I")).toBeInTheDocument();
  });
});
