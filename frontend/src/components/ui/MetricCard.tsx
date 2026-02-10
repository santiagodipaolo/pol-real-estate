interface MetricCardProps {
  title: string;
  value: string | number | null;
  subtitle?: string;
  delta?: number | null;
  deltaLabel?: string;
  prefix?: string;
  suffix?: string;
  icon?: React.ReactNode;
  accent?: "indigo" | "emerald" | "amber" | "rose" | "slate";
}

const accentColors = {
  indigo: "bg-indigo-50 text-indigo-600",
  emerald: "bg-emerald-50 text-emerald-600",
  amber: "bg-amber-50 text-amber-600",
  rose: "bg-rose-50 text-rose-600",
  slate: "bg-slate-100 text-slate-600",
};

export default function MetricCard({
  title,
  value,
  subtitle,
  delta,
  deltaLabel,
  prefix = "",
  suffix = "",
  icon,
  accent = "slate",
}: MetricCardProps) {
  const formattedValue =
    value === null || value === undefined
      ? "\u2014"
      : typeof value === "number"
        ? `${prefix}${value.toLocaleString("es-AR", { maximumFractionDigits: 0 })}${suffix}`
        : `${prefix}${value}${suffix}`;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-5 card-hover">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-slate-500 font-medium truncate">{title}</p>
          <p className="text-[22px] font-bold text-slate-900 mt-1.5 tracking-tight">{formattedValue}</p>
          <div className="flex items-center gap-2 mt-1.5">
            {delta !== undefined && delta !== null && (
              <span
                className={`inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded-md ${
                  delta >= 0
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-rose-50 text-rose-700"
                }`}
              >
                {delta >= 0 ? "\u2191" : "\u2193"}
                {Math.abs(delta).toFixed(1)}%
              </span>
            )}
            {(deltaLabel || subtitle) && (
              <span className="text-[11px] text-slate-400 truncate">{deltaLabel || subtitle}</span>
            )}
          </div>
        </div>
        {icon && (
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${accentColors[accent]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
