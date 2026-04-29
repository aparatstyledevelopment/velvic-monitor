import type { Config } from "tailwindcss";

/**
 * Tailwind utilities map onto our design tokens (CSS variables in
 * src/design/tokens.css). Components must NOT use literal Tailwind colors,
 * spacings, or radii outside this map. If you reach for a value that's not
 * here, extend the token system first.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      surface: {
        DEFAULT: "var(--surface-default)",
        inverted: "var(--surface-inverted)",
      },
      text: {
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        tertiary: "var(--text-tertiary)",
      },
      border: {
        DEFAULT: "var(--border-default)",
      },
      signal: {
        positive: "var(--signal-positive)",
        negative: "var(--signal-negative)",
      },
      track: {
        DEFAULT: "var(--track-default)",
      },
    },
    spacing: {
      0: "0",
      xxs: "var(--space-xxs)",
      xs: "var(--space-xs)",
      sm: "var(--space-sm)",
      md: "var(--space-md)",
      lg: "var(--space-lg)",
      xl: "var(--space-xl)",
      "2xl": "var(--space-2xl)",
      "3xl": "var(--space-3xl)",
    },
    borderRadius: {
      none: "var(--radius-none)",
      sm: "var(--radius-sm)",
      md: "var(--radius-md)",
      lg: "var(--radius-lg)",
      xl: "var(--radius-xl)",
      pill: "var(--radius-pill)",
    },
    fontFamily: {
      sans: "var(--font-sans)",
      mono: "var(--font-mono)",
    },
    extend: {
      transitionDuration: {
        fast: "var(--motion-fast)",
        medium: "var(--motion-medium)",
        slow: "var(--motion-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
      },
    },
  },
  plugins: [],
};

export default config;
