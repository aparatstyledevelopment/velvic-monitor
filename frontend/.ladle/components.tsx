import "../src/index.css";
import { useEffect } from "react";
import type { GlobalProvider } from "@ladle/react";

/**
 * Wraps every story so it inherits our design tokens (loaded via index.css)
 * and so the Ladle theme toggle drives our `data-theme` attribute on <html>.
 */
export const Provider: GlobalProvider = ({ children, globalState }) => {
  useEffect(() => {
    const theme = globalState.theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
  }, [globalState.theme]);
  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "var(--space-xl)",
        background: "var(--surface-default)",
        color: "var(--text-primary)",
      }}
    >
      {children}
    </div>
  );
};
