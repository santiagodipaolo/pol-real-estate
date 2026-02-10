"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { PriceTrendPoint } from "@/lib/api";

interface PriceTrendChartProps {
  data: PriceTrendPoint[];
  title?: string;
}

export default function PriceTrendChart({ data, title }: PriceTrendChartProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Sin datos disponibles
      </div>
    );
  }

  return (
    <div>
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => {
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getFullYear().toString().slice(2)}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `$${(v as number).toLocaleString()}`}
          />
          <Tooltip
            formatter={(value) => [
              `$${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}/m2`,
              "Precio",
            ]}
            labelFormatter={(label) => new Date(label).toLocaleDateString("es-AR")}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="price_m2"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            name="USD/m2"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
