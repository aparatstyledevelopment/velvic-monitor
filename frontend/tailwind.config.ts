import type { Config } from "tailwindcss";

/**
 * Tailwind utilities map onto our design tokens (CSS variables in
 * src/design/tokens.css). Components must NOT use literal Tailwind colors,
 * spacings, radii, or shadows outside this map. If you reach for a value
 * that's not here, extend the token system first.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      surface: {
        DEFAULT: "var(--surface-default)",
        muted: "var(--surface-muted)",
        sunken: "var(--surface-sunken)",
        inverted: "var(--surface-inverted)",
      },
      text: {
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        tertiary: "var(--text-tertiary)",
        quaternary: "var(--text-quaternary)",
      },
      border: {
        DEFAULT: "var(--border-default)",
        strong: "var(--border-strong)",
      },
      signal: {
        positive: "var(--signal-positive)",
        negative: "var(--signal-negative)",
      },
      track: {
        DEFAULT: "var(--track-default)",
        emphasized: "var(--track-emphasized)",
      },
    },
    spacing: {
      0: "0",
      px: "1px",
      xxs: "var(--space-xxs)",
      xs: "var(--space-xs)",
      "2xs": "var(--space-2xs)",
      sm: "var(--space-sm)",
      md: "var(--space-md)",
      lg: "var(--space-lg)",
      xl: "var(--space-xl)",
      "2xl": "var(--space-2xl)",
      "3xl": "var(--space-3xl)",
      "4xl": "var(--space-4xl)",
      "5xl": "var(--space-5xl)",
    },
    borderRadius: {
      none: "var(--radius-none)",
      sm: "var(--radius-sm)",
      md: "var(--radius-md)",
      lg: "var(--radius-lg)",
      xl: "var(--radius-xl)",
      pill: "var(--radius-pill)",
    },
    boxShadow: {
      none: "none",
      xs: "var(--shadow-xs)",
      sm: "var(--shadow-sm)",
      md: "var(--shadow-md)",
      lg: "var(--shadow-lg)",
    },
    fontFamily: {
      sans: "var(--font-sans)",
      mono: "var(--font-mono)",
    },
    fontSize: {
      "2xs": ["var(--font-size-2xs)", { lineHeight: "1.4" }],
      xs: ["var(--font-size-xs)", { lineHeight: "1.4" }],
      sm: ["var(--font-size-sm)", { lineHeight: "1.4" }],
      md: ["var(--font-size-md)", { lineHeight: "1.45" }],
      base: ["var(--font-size-base)", { lineHeight: "1.55" }],
      lg: ["var(--font-size-lg)", { lineHeight: "1.45" }],
      xl: ["var(--font-size-xl)", { lineHeight: "1.4" }],
      "2xl": ["var(--font-size-2xl)", { lineHeight: "1.25" }],
      "3xl": ["var(--font-size-3xl)", { lineHeight: "1.18" }],
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
      height: {
        "control-sm": "var(--control-height-sm)",
        "control-md": "var(--control-height-md)",
        "control-lg": "var(--control-height-lg)",
        "control-xl": "var(--control-height-xl)",
        bar: "var(--bar-height)",
        "avatar-sm": "var(--avatar-sm)",
        "avatar-md": "var(--avatar-md)",
      },
      width: {
        "control-sm": "var(--control-height-sm)",
        "control-md": "var(--control-height-md)",
        "control-lg": "var(--control-height-lg)",
        "control-xl": "var(--control-height-xl)",
        "avatar-sm": "var(--avatar-sm)",
        "avatar-md": "var(--avatar-md)",
        sidebar: "var(--sidebar-width)",
        "artifact-pane": "var(--artifact-pane-width)",
        "artifact-pane-xl": "var(--artifact-pane-width-xl)",
        search: "var(--search-width)",
      },
      maxWidth: {
        reading: "var(--reading-column)",
        auth: "var(--auth-form-width)",
      },
      inset: {
        sidebar: "var(--sidebar-width)",
        bar: "var(--bar-height)",
      },
      margin: {
        bar: "var(--bar-height)",
      },
    },
  },
  plugins: [],
};

export default config;
