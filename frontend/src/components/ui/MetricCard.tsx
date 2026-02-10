interface MetricCardProps {
  title: string;
  value: string | number | null;
  subtitle?: string;
  delta?: number | null;
  deltaLabel?: string;
  prefix?: string;
  suffix?: string;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  delta,
  deltaLabel,
  prefix = "",
  suffix = "",
}: MetricCardProps) {
  const formattedValue =
    value === null || value === undefined
      ? "—"
      : typeof value === "number"
        ? `${prefix}${value.toLocaleString("es-AR", { maximumFractionDigits: 0 })}${suffix}`
        : `${prefix}${value}${suffix}`;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{formattedValue}</p>
      <div className="flex items-center gap-2 mt-2">
        {delta !== undefined && delta !== null && (
          <span
            className={`text-sm font-medium ${
              delta >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {delta >= 0 ? "+" : ""}
            {delta.toFixed(1)}%
          </span>
        )}
        {(deltaLabel || subtitle) && (
          <span className="text-xs text-gray-400">{deltaLabel || subtitle}</span>
        )}
      </div>
    </div>
  );
}
