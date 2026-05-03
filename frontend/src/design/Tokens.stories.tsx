import type { Story } from "@ladle/react";

export default {
  title: "Tokens",
};

// ----- Colors --------------------------------------------------------------

const SEMANTIC_COLORS: { name: string; cssVar: string; description: string }[] = [
  { name: "surface-default", cssVar: "--surface-default", description: "Page background, cards" },
  { name: "surface-inverted", cssVar: "--surface-inverted", description: "Inverted surfaces" },
  { name: "text-primary", cssVar: "--text-primary", description: "Body copy, headings" },
  { name: "text-secondary", cssVar: "--text-secondary", description: "Muted body, labels" },
  { name: "text-tertiary", cssVar: "--text-tertiary", description: "Placeholders, meta" },
  { name: "border-default", cssVar: "--border-default", description: "Hairlines, dividers" },
  { name: "track-default", cssVar: "--track-default", description: "Hover wash, sliders" },
  { name: "signal-positive", cssVar: "--signal-positive", description: "Positive moves" },
  { name: "signal-negative", cssVar: "--signal-negative", description: "Negative moves" },
];

export const Colors: Story = () => (
  <Section title="Semantic colors">
    <p className="t-small" style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
      Components reference semantic tokens only. Switch the theme (top bar) to see how each role
      adapts. Signals stay constant across themes per design blueprint §1.1.
    </p>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: 16,
      }}
    >
      {SEMANTIC_COLORS.map((c) => (
        <div
          key={c.name}
          style={{
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            background: "var(--surface-default)",
          }}
        >
          <div
            style={{
              height: 64,
              background: `var(${c.cssVar})`,
              borderBottom: "1px solid var(--border-default)",
            }}
          />
          <div style={{ padding: 12 }}>
            <div className="t-mono" style={{ fontSize: 12 }}>{c.cssVar}</div>
            <div className="t-small" style={{ marginTop: 4 }}>{c.description}</div>
          </div>
        </div>
      ))}
    </div>
  </Section>
);

// ----- Spacing --------------------------------------------------------------

const SPACING = ["xxs", "xs", "sm", "md", "lg", "xl", "2xl", "3xl"] as const;

export const Spacing: Story = () => (
  <Section title="Spacing scale">
    <p className="t-small" style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
      Base unit 4px. Tailwind utilities map onto these tokens; literal pixel values
      should be unreachable from component code.
    </p>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {SPACING.map((name) => (
        <div key={name} style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div className="t-mono" style={{ width: 80, fontSize: 12 }}>--space-{name}</div>
          <div
            style={{
              height: 16,
              width: `var(--space-${name})`,
              background: "var(--text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
          />
          <div
            className="t-small"
            style={{ color: "var(--text-tertiary)" }}
          >
            <ResolvedValue cssVar={`--space-${name}`} />
          </div>
        </div>
      ))}
    </div>
  </Section>
);

// ----- Radii ----------------------------------------------------------------

const RADII = ["none", "sm", "md", "lg", "xl", "pill"] as const;

export const Radii: Story = () => (
  <Section title="Radius scale">
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
        gap: 16,
      }}
    >
      {RADII.map((name) => (
        <div key={name} style={{ textAlign: "center" }}>
          <div
            style={{
              height: 80,
              background: "var(--text-primary)",
              borderRadius: `var(--radius-${name})`,
              marginBottom: 8,
            }}
          />
          <div className="t-mono" style={{ fontSize: 12 }}>--radius-{name}</div>
          <div className="t-small" style={{ color: "var(--text-tertiary)" }}>
            <ResolvedValue cssVar={`--radius-${name}`} />
          </div>
        </div>
      ))}
    </div>
  </Section>
);

// ----- Typography -----------------------------------------------------------

export const Typography: Story = () => (
  <Section title="Type scale">
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <Sample className="t-display" label=".t-display">
        Why did VOLV-B move yesterday?
      </Sample>
      <Sample className="t-title" label=".t-title">
        Drivers
      </Sample>
      <Sample className="t-section" label=".t-section">
        Today's price action
      </Sample>
      <Sample className="t-body" label=".t-body">
        VOLV-B closed at 247.20 SEK, down 2.1% on the session, against an OMX Stockholm
        PI return of +0.4%. The relative underperformance lines up with the morning's
        downward revision to FY26 truck guidance.
      </Sample>
      <Sample className="t-small" label=".t-small">
        Last updated 2026-04-29 17:30 CET.
      </Sample>
      <Sample className="t-meta" label=".t-meta">
        regulatory · MAR-flagged
      </Sample>
      <Sample className="t-mono" label=".t-mono">
        engine_call_id: ec_8f3a3b1c
      </Sample>
    </div>
  </Section>
);

// ----- Helpers --------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h2 className="t-title">{title}</h2>
      {children}
    </div>
  );
}

function Sample({
  className,
  label,
  children,
}: {
  className: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="t-mono" style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 4 }}>
        {label}
      </div>
      <div className={className}>{children}</div>
    </div>
  );
}

function ResolvedValue({ cssVar }: { cssVar: string }) {
  // Read the resolved value from the document at render time.
  if (typeof window === "undefined") return null;
  const v = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
  return <span className="t-mono" style={{ fontSize: 11 }}>{v || "?"}</span>;
}
