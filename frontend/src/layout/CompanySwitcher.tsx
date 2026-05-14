import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../design/primitives";
import type { CompanyOut } from "../api/companies";

interface CompanySwitcherProps {
  companies: CompanyOut[];
  activeCompanyId: number | null;
  onSelect: (id: number) => void;
}

export function CompanySwitcher({
  companies,
  activeCompanyId,
  onSelect,
}: CompanySwitcherProps) {
  const active = companies.find((c) => c.id === activeCompanyId) ?? companies[0];
  if (active === undefined) {
    return (
      <div className="flex items-center gap-sm px-md py-sm text-text-tertiary t-small">
        No companies in scope
      </div>
    );
  }

  if (companies.length === 1) {
    return (
      <div
        className="flex items-center gap-sm px-md py-sm rounded-md"
        aria-label={`Active company ${active.name}`}
      >
        <CompanyLabel company={active} />
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center justify-between gap-sm px-md py-sm rounded-md hover:bg-track focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
          aria-label={`Active company ${active.name}, switch`}
        >
          <CompanyLabel company={active} />
          <span aria-hidden="true" className="text-text-tertiary text-sm">
            ▾
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {companies.map((c) => (
          <DropdownMenuItem key={c.id} onSelect={() => onSelect(c.id)}>
            <CompanyLabel company={c} />
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function CompanyLabel({ company }: { company: CompanyOut }) {
  return (
    <span className="flex items-center gap-sm min-w-0">
      <span className="t-mono text-sm text-text-tertiary shrink-0">{company.ticker}</span>
      <span className="t-body truncate">{company.name}</span>
    </span>
  );
}
