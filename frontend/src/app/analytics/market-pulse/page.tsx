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

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-56 bg-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
        <div className="h-48 bg-white rounded-2xl border border-slate-100 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-[460px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
          <div className="h-[460px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
        </div>
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
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Market Pulse</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Indicadores de salud del mercado inmobiliario de Buenos Aires (CABA)
        </p>
        {pulse?.snapshot_date && (
          <p className="text-xs text-slate-400 mt-1">
            Ultimo snapshot:{" "}
            {new Date(pulse.snapshot_date).toLocaleDateString("es-AR", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <MetricCard
          title="Listings Activos"
          value={pulse?.active_listings ?? null}
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg>}
          accent="indigo"
        />
        <MetricCard
          title="Nuevos (7d)"
          value={pulse?.new_7d ?? null}
          subtitle="ultimos 7 dias"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>}
          accent="emerald"
        />
        <MetricCard
          title="Removidos (7d)"
          value={pulse?.removed_7d ?? null}
          subtitle="ultimos 7 dias"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" /></svg>}
          accent="rose"
        />
        <MetricCard
          title="Flujo Neto (7d)"
          value={netFlow}
          delta={netFlow != null && pulse != null && pulse.active_listings > 0
            ? (netFlow / pulse.active_listings) * 100
            : null}
          deltaLabel="del total"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg>}
          accent="amber"
        />
        <MetricCard
          title="Dias en Mercado"
          value={pulse?.avg_dom != null ? Math.round(pulse.avg_dom) : null}
          suffix=" dias"
          subtitle="promedio"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
          accent="slate"
        />
        <MetricCard
          title="Precio Mediana"
          value={pulse?.median_price_usd_m2 ?? null}
          prefix="$"
          suffix="/m2"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
          accent="indigo"
        />
      </div>

      {/* Absorption Rate */}
      <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Tasa de Absorcion
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Porcentaje de listings vendidos/alquilados por semana
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-slate-900 tracking-tight">
              {pulse?.absorption_rate != null
                ? `${pulse.absorption_rate.toFixed(1)}%`
                : "\u2014"}
            </p>
            {absorptionLabel && (
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-semibold mt-1 ${
                  pulse?.absorption_rate != null && pulse.absorption_rate >= 20
                    ? "bg-rose-50 text-rose-700"
                    : pulse?.absorption_rate != null && pulse.absorption_rate >= 10
                      ? "bg-amber-50 text-amber-700"
                      : "bg-indigo-50 text-indigo-700"
                }`}
              >
                {absorptionLabel}
              </span>
            )}
          </div>
        </div>
        <div className="mt-5">
          <div className="w-full bg-slate-100 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${
                pulse?.absorption_rate != null && pulse.absorption_rate >= 20
                  ? "bg-rose-500"
                  : pulse?.absorption_rate != null && pulse.absorption_rate >= 10
                    ? "bg-amber-500"
                    : "bg-indigo-500"
              }`}
              style={{
                width: `${Math.min(pulse?.absorption_rate ?? 0, 100)}%`,
              }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 mt-1.5">
            <span>0%</span>
            <span>10% - equilibrado</span>
            <span>20%+ - caliente</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-6">
          <BarrioBarChart
            data={listingsByBarrio}
            title="Top 15 Barrios por Cantidad de Listings"
            color="#6366f1"
            valuePrefix=""
            valueSuffix=" listings"
          />
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-6">
          <BarrioBarChart
            data={priceByBarrio}
            title="Top 15 Barrios por Precio USD/m2"
            color="#4f46e5"
            valuePrefix="$"
            valueSuffix="/m2"
          />
        </div>
      </div>

      {/* Barrios Summary Table */}
      {barrios.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Resumen por Barrio</h2>
            <span className="text-xs text-slate-400">
              {barrios.length} barrios
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Barrio</th>
                  <th className="px-4 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Listings</th>
                  <th className="px-4 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Mediana USD/m2</th>
                  <th className="px-4 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Promedio USD/m2</th>
                  <th className="px-4 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Dias en Mercado</th>
                  <th className="px-4 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Yield Est.</th>
                </tr>
              </thead>
              <tbody>
                {barrios
                  .sort((a, b) => (b.listing_count ?? 0) - (a.listing_count ?? 0))
                  .slice(0, 20)
                  .map((b, idx) => (
                    <tr
                      key={b.id}
                      className={`border-b border-slate-50 hover:bg-slate-50/50 transition-colors ${idx % 2 === 0 ? "" : "bg-slate-25"}`}
                    >
                      <td className="px-4 py-3 text-sm font-medium text-slate-900">
                        {b.name}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-slate-600">
                        {b.listing_count?.toLocaleString("es-AR") ?? "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-mono font-semibold text-slate-800">
                        {b.median_price_usd_m2 != null
                          ? `$${b.median_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                          : "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-mono text-slate-600">
                        {b.avg_price_usd_m2 != null
                          ? `$${b.avg_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                          : "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-slate-600">
                        {b.avg_days_on_market != null
                          ? Math.round(b.avg_days_on_market)
                          : "\u2014"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {b.rental_yield_estimate != null ? (
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ${
                              b.rental_yield_estimate >= 5
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {b.rental_yield_estimate.toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-sm text-slate-400">{"\u2014"}</span>
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
