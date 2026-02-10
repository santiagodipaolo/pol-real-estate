"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PriceTrendPoint } from "@/lib/api";

interface PriceTrendChartProps {
  data: PriceTrendPoint[];
  title?: string;
}

export default function PriceTrendChart({ data, title }: PriceTrendChartProps) {
  if (!data.length) {
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
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickFormatter={(v) => {
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getFullYear().toString().slice(2)}`;
            }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickFormatter={(v) => `$${(v as number).toLocaleString()}`}
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
              `$${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}/m2`,
              "Precio",
            ]}
            labelFormatter={(label) => new Date(label).toLocaleDateString("es-AR")}
            cursor={{ stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 }}
          />
          <Line
            type="monotone"
            dataKey="price_m2"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4, fill: "#6366f1", stroke: "white", strokeWidth: 2 }}
            name="USD/m2"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
