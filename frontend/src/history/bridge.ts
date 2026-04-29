import { useEffect } from "react";

/**
 * Browser-back history bridge for modal surfaces (full-page screens, takeovers,
 * mobile artifact pane, dialogs). Pushes a sentinel state on activation; the
 * back button pops the sentinel and triggers `onClose`. On unmount while still
 * sentinel-on-top, pops it cleanly so the back stack doesn't leak.
 *
 * See design blueprint §5.7 (universal-close behavior) and frontend AGENTS.md.
 */
export function useHistoryBridge(active: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!active) return;
    history.pushState({ sentinel: true }, "");
    const onPop = () => onClose();
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
      const state = history.state as { sentinel?: boolean } | null;
      if (state?.sentinel) {
        history.back();
      }
    };
  }, [active, onClose]);
}
