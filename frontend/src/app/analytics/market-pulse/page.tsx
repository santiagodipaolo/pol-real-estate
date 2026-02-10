"use client";

import { useEffect, useState } from "react";
import MetricCard from "@/components/ui/MetricCard";
import BarrioBarChart from "@/components/charts/BarrioBarChart";
import {
  getMarketPulse,
  getBarrios,
  type MarketPulse,
  type BarrioWithStats,
} from "@/lib/api";

export default function MarketPulsePage() {
  const [pulse, setPulse] = useState<MarketPulse | null>(null);
  const [barrios, setBarrios] = useState<BarrioWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getMarketPulse(), getBarrios()])
      .then(([pulseData, barriosData]) => {
        setPulse(pulseData);
        setBarrios(barriosData);
      })
      .catch(() => setError("Error al cargar datos del mercado."))
      .finally(() => setLoading(false));
  }, []);

  const listingsByBarrio = barrios
    .filter((b) => b.listing_count != null && b.listing_count > 0)
    .sort((a, b) => (b.listing_count ?? 0) - (a.listing_count ?? 0))
    .slice(0, 15)
    .map((b) => ({
      name: b.name,
      value: b.listing_count,
      slug: b.slug,
    }));

  const priceByBarrio = barrios
    .filter((b) => b.median_price_usd_m2 != null)
    .sort((a, b) => (b.median_price_usd_m2 ?? 0) - (a.median_price_usd_m2 ?? 0))
    .slice(0, 15)
    .map((b) => ({
      name: b.name,
      value: b.median_price_usd_m2,
      slug: b.slug,
    }));

  // Compute net flow and absorption context
  const netFlow =
    pulse != null ? pulse.new_7d - pulse.removed_7d : null;
  const absorptionLabel =
    pulse?.absorption_rate != null
      ? pulse.absorption_rate >= 20
        ? "Mercado caliente"
        : pulse.absorption_rate >= 10
          ? "Mercado equilibrado"
          : "Mercado frio"
      : undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Market Pulse</h1>
        <p className="text-sm text-gray-500 mt-1">
          Indicadores de salud del mercado inmobiliario de Buenos Aires (CABA)
        </p>
        {pulse?.snapshot_date && (
          <p className="text-xs text-gray-400 mt-1">
            Ultimo snapshot:{" "}
            {new Date(pulse.snapshot_date).toLocaleDateString("es-AR", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
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
            Cargando datos del mercado...
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <MetricCard
              title="Listings Activos"
              value={pulse?.active_listings ?? null}
            />
            <MetricCard
              title="Nuevos (7d)"
              value={pulse?.new_7d ?? null}
              subtitle="ultimos 7 dias"
            />
            <MetricCard
              title="Removidos (7d)"
              value={pulse?.removed_7d ?? null}
              subtitle="ultimos 7 dias"
            />
            <MetricCard
              title="Flujo Neto (7d)"
              value={netFlow}
              delta={netFlow != null && pulse != null && pulse.active_listings > 0
                ? (netFlow / pulse.active_listings) * 100
                : null}
              deltaLabel="del total"
            />
            <MetricCard
              title="Dias en Mercado"
              value={
                pulse?.avg_dom != null ? Math.round(pulse.avg_dom) : null
              }
              suffix=" dias"
              subtitle="promedio"
            />
            <MetricCard
              title="Precio Mediana"
              value={pulse?.median_price_usd_m2 ?? null}
              prefix="$"
              suffix="/m2"
            />
          </div>

          {/* Absorption Rate */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Tasa de Absorcion
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Porcentaje de listings vendidos/alquilados por semana
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-gray-900">
                  {pulse?.absorption_rate != null
                    ? `${pulse.absorption_rate.toFixed(1)}%`
                    : "—"}
                </p>
                {absorptionLabel && (
                  <p
                    className={`text-sm font-medium mt-1 ${
                      pulse?.absorption_rate != null && pulse.absorption_rate >= 20
                        ? "text-red-600"
                        : pulse?.absorption_rate != null && pulse.absorption_rate >= 10
                          ? "text-yellow-600"
                          : "text-blue-600"
                    }`}
                  >
                    {absorptionLabel}
                  </p>
                )}
              </div>
            </div>
            {/* Visual bar */}
            <div className="mt-4">
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-500 ${
                    pulse?.absorption_rate != null && pulse.absorption_rate >= 20
                      ? "bg-red-500"
                      : pulse?.absorption_rate != null && pulse.absorption_rate >= 10
                        ? "bg-yellow-500"
                        : "bg-blue-500"
                  }`}
                  style={{
                    width: `${Math.min(pulse?.absorption_rate ?? 0, 100)}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0%</span>
                <span>10% - equilibrado</span>
                <span>20%+ - caliente</span>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <BarrioBarChart
                data={listingsByBarrio}
                title="Top 15 Barrios por Cantidad de Listings"
                color="#6366f1"
                valuePrefix=""
                valueSuffix=" listings"
              />
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <BarrioBarChart
                data={priceByBarrio}
                title="Top 15 Barrios por Precio USD/m2"
                color="#2563eb"
                valuePrefix="$"
                valueSuffix="/m2"
              />
            </div>
          </div>

          {/* Barrios Summary Table */}
          {barrios.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Resumen por Barrio</h2>
                <span className="text-sm text-gray-400">
                  {barrios.length} barrios
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-medium text-gray-600">Barrio</th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">
                        Listings
                      </th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">
                        Mediana USD/m2
                      </th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">
                        Promedio USD/m2
                      </th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">
                        Dias en Mercado
                      </th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">
                        Yield Est.
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {barrios
                      .sort((a, b) => (b.listing_count ?? 0) - (a.listing_count ?? 0))
                      .slice(0, 20)
                      .map((b) => (
                        <tr
                          key={b.id}
                          className="hover:bg-gray-50 transition-colors"
                        >
                          <td className="px-4 py-3 font-medium text-gray-900">
                            {b.name}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {b.listing_count?.toLocaleString("es-AR") ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {b.median_price_usd_m2 != null
                              ? `$${b.median_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                              : "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {b.avg_price_usd_m2 != null
                              ? `$${b.avg_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                              : "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {b.avg_days_on_market != null
                              ? Math.round(b.avg_days_on_market)
                              : "—"}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {b.rental_yield_estimate != null ? (
                              <span
                                className={`font-medium ${
                                  b.rental_yield_estimate >= 5
                                    ? "text-green-600"
                                    : "text-gray-700"
                                }`}
                              >
                                {b.rental_yield_estimate.toFixed(2)}%
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
        </>
      )}
    </div>
  );
}
