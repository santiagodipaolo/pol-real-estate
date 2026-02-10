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

  // Compute summary stats
  const avgGross =
    sorted.length > 0
      ? sorted.reduce((sum, d) => sum + (d.gross_rental_yield ?? 0), 0) / sorted.length
      : null;
  const avgNet =
    sorted.length > 0
      ? sorted.reduce((sum, d) => sum + (d.net_rental_yield ?? 0), 0) / sorted.length
      : null;
  const bestYield = sorted.length > 0 ? sorted[0] : null;

  const SortIcon = ({ active, dir }: { active: boolean; dir: SortDir }) => (
    <span className="ml-1 inline-block">
      {active ? (dir === "desc" ? "\u2193" : "\u2191") : "\u2195"}
    </span>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Rentabilidad por Barrio</h1>
        <p className="text-sm text-gray-500 mt-1">
          Rendimiento bruto y neto estimado por barrio en Buenos Aires (CABA)
        </p>
      </div>

      {/* KPI Cards */}
      {!loading && !error && sorted.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Yield Bruto Promedio"
            value={avgGross != null ? avgGross.toFixed(2) : null}
            suffix="%"
          />
          <MetricCard
            title="Yield Neto Promedio"
            value={avgNet != null ? avgNet.toFixed(2) : null}
            suffix="%"
          />
          <MetricCard
            title="Mejor Barrio (Bruto)"
            value={bestYield?.barrio_name ?? null}
            subtitle={
              bestYield?.gross_rental_yield != null
                ? `${bestYield.gross_rental_yield.toFixed(2)}%`
                : undefined
            }
          />
          <MetricCard
            title="Barrios Analizados"
            value={sorted.length}
          />
        </div>
      )}

      {/* Bar Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold mb-4">
          Top 20 Barrios por Rentabilidad Bruta
        </h2>
        {loading ? (
          <div className="flex items-center justify-center h-80">
            <div className="flex items-center gap-3 text-gray-400">
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Cargando datos...
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-80 text-red-500">
            {error}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={500}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                type="number"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
                domain={[0, "auto"]}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11 }}
                width={100}
              />
              <Tooltip
                formatter={(value) => [
                  `${Number(value).toFixed(2)}%`,
                ]}
              />
              <Bar dataKey="gross" name="Bruto" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-gross-${index}`}
                    fill={entry.gross >= (avgGross ?? 0) ? "#16a34a" : "#2563eb"}
                  />
                ))}
              </Bar>
              <Bar dataKey="net" name="Neto" fill="#94a3b8" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Table */}
      {!loading && !error && sorted.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold">Detalle por Barrio</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">#</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Barrio</th>
                  <th
                    className="px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => handleSort("median_sale_price_usd_m2")}
                  >
                    Precio Venta USD/m2
                    <SortIcon
                      active={sortKey === "median_sale_price_usd_m2"}
                      dir={sortDir}
                    />
                  </th>
                  <th
                    className="px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => handleSort("median_rent_usd_m2")}
                  >
                    Alquiler USD/m2
                    <SortIcon
                      active={sortKey === "median_rent_usd_m2"}
                      dir={sortDir}
                    />
                  </th>
                  <th
                    className="px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => handleSort("gross_rental_yield")}
                  >
                    Yield Bruto
                    <SortIcon
                      active={sortKey === "gross_rental_yield"}
                      dir={sortDir}
                    />
                  </th>
                  <th
                    className="px-4 py-3 font-medium text-gray-600 cursor-pointer hover:text-gray-900 select-none"
                    onClick={() => handleSort("net_rental_yield")}
                  >
                    Yield Neto
                    <SortIcon
                      active={sortKey === "net_rental_yield"}
                      dir={sortDir}
                    />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sorted.map((row, idx) => (
                  <tr
                    key={row.barrio_id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-400">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/barrios/${row.slug}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {row.barrio_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {row.median_sale_price_usd_m2 != null
                        ? `$${row.median_sale_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {row.median_rent_usd_m2 != null
                        ? `$${row.median_rent_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {row.gross_rental_yield != null ? (
                        <span
                          className={`font-semibold ${
                            row.gross_rental_yield >= (avgGross ?? 0)
                              ? "text-green-600"
                              : "text-gray-700"
                          }`}
                        >
                          {row.gross_rental_yield.toFixed(2)}%
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {row.net_rental_yield != null ? (
                        <span className="text-gray-700">
                          {row.net_rental_yield.toFixed(2)}%
                        </span>
                      ) : (
                        "—"
                      )}
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
