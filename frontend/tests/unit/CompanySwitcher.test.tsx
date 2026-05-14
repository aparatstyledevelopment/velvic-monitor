import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CompanySwitcher } from "../../src/layout/CompanySwitcher";
import type { CompanyOut } from "../../src/api/companies";

const VOLV: CompanyOut = {
  id: 1,
  ticker: "VOLV-B",
  name: "Volvo Group",
  market: "Nasdaq Stockholm",
  sector: "Industrials",
  is_primary: true,
};
const SAND: CompanyOut = {
  id: 2,
  ticker: "SAND",
  name: "Sandvik",
  market: "Nasdaq Stockholm",
  sector: "Industrials",
  is_primary: false,
};

describe("CompanySwitcher", () => {
  it("flattens to a static label when only one company is in scope", () => {
    render(<CompanySwitcher companies={[VOLV]} activeCompanyId={1} onSelect={vi.fn()} />);
    expect(screen.getByText("Volvo Group")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders an empty hint when no companies are in scope", () => {
    render(<CompanySwitcher companies={[]} activeCompanyId={null} onSelect={vi.fn()} />);
    expect(screen.getByText(/no companies in scope/i)).toBeInTheDocument();
  });

  it("renders a dropdown trigger when scope has multiple companies", () => {
    render(
      <CompanySwitcher companies={[VOLV, SAND]} activeCompanyId={1} onSelect={vi.fn()} />,
    );
    const trigger = screen.getByRole("button", { name: /active company volvo group/i });
    expect(trigger).toBeInTheDocument();
  });

  it("falls back to the first company when activeCompanyId is null", () => {
    render(
      <CompanySwitcher companies={[VOLV, SAND]} activeCompanyId={null} onSelect={vi.fn()} />,
    );
    const trigger = screen.getByRole("button", { name: /active company volvo group/i });
    expect(trigger).toBeInTheDocument();
  });

});
