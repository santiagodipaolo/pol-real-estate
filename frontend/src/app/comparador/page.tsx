"use client";

import { useState, useEffect, useMemo } from "react";
import { getBarrios, compareBarrios, type BarrioWithStats, type BarrioComparison } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = ["#6366f1", "#10b981", "#f59e0b"];

const METRIC_CONFIG: { key: string; label: string; format: (v: number | null) => string; higherBetter: boolean }[] = [
  {
    key: "median_price_usd_m2",
    label: "Mediana USD/m\u00b2",
    format: (v) => (v != null ? `$${v.toLocaleString("es-AR", { maximumFractionDigits: 0 })}` : "\u2014"),
    higherBetter: false,
  },
  {
    key: "avg_price_usd_m2",
    label: "Promedio USD/m\u00b2",
    format: (v) => (v != null ? `$${v.toLocaleString("es-AR", { maximumFractionDigits: 0 })}` : "\u2014"),
    higherBetter: false,
  },
  {
    key: "listing_count",
    label: "Publicaciones",
    format: (v) => (v != null ? String(Math.round(v)) : "\u2014"),
    higherBetter: true,
  },
  {
    key: "avg_days_on_market",
    label: "D\u00edas en mercado",
    format: (v) => (v != null ? `${Math.round(v)} d\u00edas` : "\u2014"),
    higherBetter: false,
  },
  {
    key: "rental_yield_estimate",
    label: "Rental Yield",
    format: (v) => (v != null ? `${v.toFixed(1)}%` : "\u2014"),
    higherBetter: true,
  },
];

export default function ComparadorPage() {
  const [allBarrios, setAllBarrios] = useState<BarrioWithStats[]>([]);
  const [selectedSlugs, setSelectedSlugs] = useState<string[]>([]);
  const [comparison, setComparison] = useState<BarrioComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getBarrios()
      .then(setAllBarrios)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedSlugs.length < 2) {
      setComparison(null);
      return;
    }
    setLoading(true);
    compareBarrios(selectedSlugs)
      .then(setComparison)
      .catch(() => setComparison(null))
      .finally(() => setLoading(false));
  }, [selectedSlugs]);

  const filtered = useMemo(() => {
    if (!search) return allBarrios;
    const q = search.toLowerCase();
    return allBarrios.filter((b) => b.name.toLowerCase().includes(q));
  }, [allBarrios, search]);

  const toggleBarrio = (slug: string) => {
    setSelectedSlugs((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : prev.length >= 3 ? prev : [...prev, slug]
    );
  };

  // Build trend chart data
  const trendData = useMemo(() => {
    if (!comparison) return [];
    const dateMap: Record<string, Record<string, number | null>> = {};
    comparison.barrios.forEach((b) => {
      b.trends
        .filter((t) => t.operation_type === "sale")
        .forEach((t) => {
          if (!dateMap[t.snapshot_date]) dateMap[t.snapshot_date] = {};
          dateMap[t.snapshot_date][b.slug] = t.median_price_usd_m2;
        });
    });
    return Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, values]) => ({ date, ...values }));
  }, [comparison]);

  // Determine "winner" for each metric (lowest price = best, highest yield = best)
  const getWinner = (metricKey: string, higherBetter: boolean) => {
    if (!comparison) return null;
    let best: { slug: string; value: number } | null = null;
    for (const b of comparison.barrios) {
      const v = (b as unknown as Record<string, unknown>)[metricKey] as number | null;
      if (v == null) continue;
      if (!best || (higherBetter ? v > best.value : v < best.value)) {
        best = { slug: b.slug, value: v };
      }
    }
    return best?.slug ?? null;
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Comparador de Barrios</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Seleccione hasta 3 barrios para comparar m\u00e9tricas lado a lado
        </p>
      </div>

      {/* Barrio Selector */}
      <div className="bg-white rounded-2xl border border-slate-100 p-5">
        <div className="flex items-center gap-3 mb-3">
          <input
            type="text"
            placeholder="Buscar barrio..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-3 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
          />
          {selectedSlugs.length > 0 && (
            <button
              onClick={() => setSelectedSlugs([])}
              className="px-3 py-2 rounded-xl text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
            >
              Limpiar
            </button>
          )}
        </div>

        {/* Selected chips */}
        {selectedSlugs.length > 0 && (
          <div className="flex gap-2 mb-3">
            {selectedSlugs.map((slug, i) => {
              const b = allBarrios.find((b) => b.slug === slug);
              return (
                <span
                  key={slug}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-white"
                  style={{ backgroundColor: COLORS[i] }}
                >
                  {b?.name || slug}
                  <button onClick={() => toggleBarrio(slug)} className="hover:opacity-70">
                    &times;
                  </button>
                </span>
              );
            })}
          </div>
        )}

        {/* Barrio list */}
        <div className="max-h-40 overflow-y-auto space-y-0.5">
          {filtered.map((b) => {
            const isSelected = selectedSlugs.includes(b.slug);
            const disabled = !isSelected && selectedSlugs.length >= 3;
            return (
              <button
                key={b.slug}
                onClick={() => !disabled && toggleBarrio(b.slug)}
                disabled={disabled}
                className={`w-full text-left px-3 py-1.5 rounded-lg text-sm transition-all ${
                  isSelected
                    ? "bg-indigo-50 text-indigo-700 font-medium"
                    : disabled
                    ? "text-slate-300 cursor-not-allowed"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {b.name}
                {b.comuna_name && (
                  <span className="text-xs text-slate-400 ml-2">({b.comuna_name})</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Comparison Results */}
      {loading && (
        <div className="text-center py-12 text-sm text-slate-400">Cargando comparaci\u00f3n...</div>
      )}

      {comparison && comparison.barrios.length >= 2 && (
        <>
          {/* Metrics Table */}
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    M\u00e9trica
                  </th>
                  {comparison.barrios.map((b, i) => (
                    <th
                      key={b.slug}
                      className="text-right px-5 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: COLORS[i] }}
                    >
                      {b.barrio_name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {METRIC_CONFIG.map((mc) => {
                  const winner = getWinner(mc.key, mc.higherBetter);
                  return (
                    <tr key={mc.key} className="border-b border-slate-50 last:border-0">
                      <td className="px-5 py-3 text-slate-600 font-medium">{mc.label}</td>
                      {comparison.barrios.map((b) => {
                        const val = (b as unknown as Record<string, unknown>)[mc.key] as number | null;
                        const isWinner = winner === b.slug && val != null;
                        return (
                          <td key={b.slug} className="px-5 py-3 text-right font-mono">
                            <span
                              className={
                                isWinner
                                  ? "text-emerald-600 font-semibold"
                                  : "text-slate-700"
                              }
                            >
                              {mc.format(val)}
                              {isWinner && (
                                <svg
                                  className="inline-block w-3.5 h-3.5 ml-1 text-emerald-500"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  strokeWidth={2.5}
                                  stroke="currentColor"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="m4.5 12.75 6 6 9-13.5"
                                  />
                                </svg>
                              )}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          </div>

          {/* Trend Chart */}
          {trendData.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-100 p-5">
              <h3 className="text-sm font-semibold text-slate-900 mb-4">
                Tendencia Precio Mediana USD/m\u00b2
              </h3>
              <div className="h-[250px] md:h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    tickFormatter={(d: string) => d.slice(5)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "none",
                      borderRadius: "12px",
                      fontSize: "12px",
                      color: "#e2e8f0",
                    }}
                    formatter={(value: number | undefined) => [`$${value?.toLocaleString("es-AR", { maximumFractionDigits: 0 }) ?? "\u2014"}`, undefined]}
                  />
                  <Legend />
                  {comparison.barrios.map((b, i) => (
                    <Line
                      key={b.slug}
                      type="monotone"
                      dataKey={b.slug}
                      name={b.barrio_name}
                      stroke={COLORS[i]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      {!comparison && !loading && selectedSlugs.length < 2 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-12 flex flex-col items-center justify-center text-center">
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-indigo-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Comparar barrios</h3>
          <p className="text-xs text-slate-500 max-w-md">
            Seleccione al menos 2 barrios arriba para ver la comparaci&oacute;n de m&eacute;tricas y tendencias.
          </p>
        </div>
      )}
    </div>
  );
}
