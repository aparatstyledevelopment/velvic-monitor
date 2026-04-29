import { Hairline, Pill } from "../../design/primitives";

export function DriversModule() {
  return (
    <div className="flex-1 min-w-0 px-xl py-xl flex flex-col gap-xl">
      <header className="flex items-center justify-between">
        <h1 className="t-title">Drivers</h1>
        <Pill>Phase 0 placeholder</Pill>
      </header>
      <Hairline />
      <section className="max-w-[680px]">
        <p className="t-body text-text-secondary">
          The Drivers briefing card lands here. Phase 1 wires the engine and the
          end-of-day pipeline; Phase 3 dresses this view in the full editorial
          layout from the design blueprint.
        </p>
      </section>
    </div>
  );
}
