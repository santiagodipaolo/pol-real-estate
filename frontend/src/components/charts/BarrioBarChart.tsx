"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import useIsMobile from "@/lib/hooks/useIsMobile";

interface BarrioBarChartProps {
  data: { name: string; value: number | null; slug?: string }[];
  title?: string;
  color?: string;
  valuePrefix?: string;
  valueSuffix?: string;
}

export default function BarrioBarChart({
  data,
  title,
  color = "#6366f1",
  valuePrefix = "$",
  valueSuffix = "/m2",
}: BarrioBarChartProps) {
  const isMobile = useIsMobile();
  const marginLeft = isMobile ? 50 : 80;
  const yAxisWidth = isMobile ? 50 : 80;

  const filtered = data
    .filter((d) => d.value !== null)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 15);

  if (!filtered.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        Sin datos disponibles
      </div>
    );
  }

  return (
    <div>
      {title && (
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        </div>
      )}
      <div className="h-[300px] md:h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filtered} layout="vertical" margin={{ left: marginLeft, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickFormatter={(v) => `${valuePrefix}${(v as number).toLocaleString()}`}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: "#475569" }}
            width={yAxisWidth}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              fontSize: "12px",
              padding: "8px 12px",
            }}
            formatter={(value) => [
              `${valuePrefix}${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}${valueSuffix}`,
              "Valor",
            ]}
            cursor={{ fill: "rgba(99, 102, 241, 0.05)" }}
          />
          <Bar dataKey="value" fill={color} radius={[0, 6, 6, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
