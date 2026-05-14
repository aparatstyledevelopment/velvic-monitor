interface SparklineProps {
  /** Time-ordered values (oldest → newest). */
  values: readonly number[];
  width?: number;
  height?: number;
  /** Override stroke color via CSS variable name (without var()). */
  colorVar?: string;
  className?: string;
  ariaLabel?: string;
}

export function Sparkline({
  values,
  width = 320,
  height = 80,
  colorVar = "--text-primary",
  className = "",
  ariaLabel = "Sparkline",
}: SparklineProps) {
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stride = width / (values.length - 1);

  const points = values
    .map((v, i) => {
      const x = i * stride;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  const linePath = `M ${points.replace(/ /g, " L ")}`;
  const areaPath = `${linePath} L ${width.toFixed(2)},${height.toFixed(2)} L 0,${height.toFixed(2)} Z`;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      preserveAspectRatio="none"
      className={["block", className].join(" ")}
    >
      <path
        d={areaPath}
        fill={`var(${colorVar})`}
        fillOpacity={0.06}
      />
      <path
        d={linePath}
        fill="none"
        stroke={`var(${colorVar})`}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
