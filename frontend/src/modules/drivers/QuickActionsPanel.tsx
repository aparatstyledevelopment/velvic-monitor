import { ChevronRight } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { DRIVERS_DATA_SOURCES } from "../../api/drivers";
import { useHistoryBridge } from "../../history/bridge";
import { useQuickActions } from "../../state/quickActions";

/**
 * Floating panel anchored just to the right of the sidebar, listing the
 * Drivers module's "ground-truth" data sources. Clicking an item routes
 * to the corresponding takeover view (DriversDataView), which covers
 * panes 2 and 3 with a back button.
 *
 * Positioning is fixed (not absolute) so it floats above the conversation
 * pane regardless of scroll. Click outside or press Esc to dismiss; the
 * history bridge wires the device back-button on mobile.
 */
export function QuickActionsPanel() {
  const open = useQuickActions((s) => s.open);
  const close = useQuickActions((s) => s.closePanel);
  const navigate = useNavigate();
  useHistoryBridge(open, close);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-30 lg:left-[220px]">
      <button
        type="button"
        aria-label="Close quick actions"
        className="absolute inset-0 bg-black/10"
        onClick={close}
      />
      <div
        role="dialog"
        aria-label="Drivers quick actions"
        className="relative ml-md mt-[80px] max-w-[320px] rounded-lg border border-border bg-surface shadow-md overflow-hidden"
      >
        <header className="px-lg pt-md pb-xs">
          <span className="t-meta">Drivers · ground truth</span>
        </header>
        <ul className="flex flex-col">
          {DRIVERS_DATA_SOURCES.map((s) => (
            <li key={s.key}>
              <button
                type="button"
                onClick={() => {
                  close();
                  navigate(`/drivers/data/${s.key}`);
                }}
                className="group flex w-full items-center gap-md px-lg py-md text-left border-t border-border first:border-t-0 hover:bg-surface-muted focus:outline-none focus-visible:bg-surface-muted"
              >
                <div className="flex-1 min-w-0">
                  <div className="t-label">{s.label}</div>
                  <div className="t-small text-text-tertiary truncate">
                    {s.description}
                  </div>
                </div>
                <ChevronRight
                  size={14}
                  aria-hidden="true"
                  className="text-text-tertiary group-hover:text-text-primary transition-colors"
                />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
