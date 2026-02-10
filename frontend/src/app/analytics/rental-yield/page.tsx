"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import MetricCard from "@/components/ui/MetricCard";
import { getRentalYield, type RentalYieldBarrio } from "@/lib/api";

type SortKey = "gross_rental_yield" | "net_rental_yield" | "median_sale_price_usd_m2" | "median_rent_usd_m2";
type SortDir = "asc" | "desc";

export default function RentalYieldPage() {
  const [data, setData] = useState<RentalYieldBarrio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("gross_rental_yield");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    setLoading(true);
    getRentalYield()
      .then(setData)
      .catch(() => setError("Error al cargar datos de rentabilidad."))
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...data]
    .filter((d) => d.gross_rental_yield !== null)
    .sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

  const chartData = sorted
    .filter((d) => d.gross_rental_yield !== null)
    .slice(0, 20)
    .map((d) => ({
      name: d.barrio_name,
      gross: d.gross_rental_yield != null ? Number(d.gross_rental_yield.toFixed(2)) : 0,
      net: d.net_rental_yield != null ? Number(d.net_rental_yield.toFixed(2)) : 0,
    }));

  const avgGross =
    sorted.length > 0
      ? sorted.reduce((sum, d) => sum + (d.gross_rental_yield ?? 0), 0) / sorted.length
      : null;
  const avgNet =
    sorted.length > 0
      ? sorted.reduce((sum, d) => sum + (d.net_rental_yield ?? 0), 0) / sorted.length
      : null;
  const bestYield = sorted.length > 0 ? sorted[0] : null;

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700 select-none"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortKey === field && (
          <svg className={`w-3 h-3 ${sortDir === "asc" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        )}
      </div>
    </th>
  );

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-56 bg-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
        <div className="h-[560px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Rentabilidad por Barrio</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Rendimiento bruto y neto estimado por barrio en Buenos Aires (CABA)
        </p>
      </div>

      {/* KPI Cards */}
      {sorted.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Yield Bruto Promedio"
            value={avgGross != null ? avgGross.toFixed(2) : null}
            suffix="%"
            icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" /></svg>}
            accent="emerald"
          />
          <MetricCard
            title="Yield Neto Promedio"
            value={avgNet != null ? avgNet.toFixed(2) : null}
            suffix="%"
            accent="indigo"
          />
          <MetricCard
            title="Mejor Barrio (Bruto)"
            value={bestYield?.barrio_name ?? null}
            subtitle={
              bestYield?.gross_rental_yield != null
                ? `${bestYield.gross_rental_yield.toFixed(2)}%`
                : undefined
            }
            accent="amber"
          />
          <MetricCard
            title="Barrios Analizados"
            value={sorted.length}
            accent="slate"
          />
        </div>
      )}

      {/* Bar Chart */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">
          Top 20 Barrios por Rentabilidad Bruta
        </h2>
        <ResponsiveContainer width="100%" height={500}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickFormatter={(v) => `${v}%`}
              domain={[0, "auto"]}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: "#475569" }}
              width={100}
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
                `${Number(value).toFixed(2)}%`,
              ]}
              cursor={{ fill: "rgba(99, 102, 241, 0.05)" }}
            />
            <Bar dataKey="gross" name="Bruto" radius={[0, 6, 6, 0]} barSize={14}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-gross-${index}`}
                  fill={entry.gross >= (avgGross ?? 0) ? "#10b981" : "#6366f1"}
                />
              ))}
            </Bar>
            <Bar dataKey="net" name="Neto" fill="#cbd5e1" radius={[0, 6, 6, 0]} barSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      {sorted.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-900">Detalle por Barrio</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">#</th>
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Barrio</th>
                  <SortHeader label="Precio Venta USD/m2" field="median_sale_price_usd_m2" />
                  <SortHeader label="Alquiler USD/m2" field="median_rent_usd_m2" />
                  <SortHeader label="Yield Bruto" field="gross_rental_yield" />
                  <SortHeader label="Yield Neto" field="net_rental_yield" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, idx) => (
                  <tr
                    key={row.barrio_id}
                    className={`border-b border-slate-50 hover:bg-slate-50/50 transition-colors ${idx % 2 === 0 ? "" : "bg-slate-25"}`}
                  >
                    <td className="px-4 py-3 text-xs text-slate-400">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/barrios/${row.slug}`}
                        className="text-indigo-600 hover:text-indigo-800 font-medium text-sm"
                      >
                        {row.barrio_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-slate-700">
                      {row.median_sale_price_usd_m2 != null
                        ? `$${row.median_sale_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                        : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-slate-700">
                      {row.median_rent_usd_m2 != null
                        ? `$${row.median_rent_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                        : "\u2014"}
                    </td>
                    <td className="px-4 py-3">
                      {row.gross_rental_yield != null ? (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ${
                            row.gross_rental_yield >= (avgGross ?? 0)
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {row.gross_rental_yield.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-sm text-slate-400">{"\u2014"}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {row.net_rental_yield != null
                        ? `${row.net_rental_yield.toFixed(2)}%`
                        : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
