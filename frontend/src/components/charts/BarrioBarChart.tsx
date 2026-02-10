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
  color = "#2563eb",
  valuePrefix = "$",
  valueSuffix = "/m2",
}: BarrioBarChartProps) {
  const filtered = data
    .filter((d) => d.value !== null)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 15);

  if (!filtered.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Sin datos disponibles
      </div>
    );
  }

  return (
    <div>
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={filtered} layout="vertical" margin={{ left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${valuePrefix}${(v as number).toLocaleString()}`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11 }}
            width={80}
          />
          <Tooltip
            formatter={(value) => [
              `${valuePrefix}${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}${valueSuffix}`,
              "Valor",
            ]}
          />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
