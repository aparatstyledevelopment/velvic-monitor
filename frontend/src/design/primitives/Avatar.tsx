interface AvatarProps {
  name: string | null;
  email: string;
  size?: "sm" | "md";
  className?: string;
}

function initialsFrom(name: string | null, email: string): string {
  if (name && name.trim().length > 0) {
    const parts = name.trim().split(/\s+/);
    const first = parts[0]?.[0] ?? "";
    const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
    return (first + last).toUpperCase();
  }
  return (email[0] ?? "?").toUpperCase();
}

export function Avatar({ name, email, size = "md", className = "" }: AvatarProps) {
  const sizeCls = size === "sm" ? "h-6 w-6 text-[11px]" : "h-8 w-8 text-[12px]";
  const classes = [
    "inline-flex items-center justify-center rounded-pill",
    "bg-track text-text-primary font-medium select-none",
    sizeCls,
    className,
  ].join(" ");
  return (
    <span className={classes} aria-hidden="true">
      {initialsFrom(name, email)}
    </span>
  );
}
