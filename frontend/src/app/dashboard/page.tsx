"use client";

import { useEffect, useState, useCallback } from "react";
import MetricCard from "@/components/ui/MetricCard";
import MapContainer from "@/components/map/MapContainer";
import ChoroplethLayer from "@/components/map/ChoroplethLayer";
import BarrioBarChart from "@/components/charts/BarrioBarChart";
import type maplibregl from "maplibre-gl";
import Link from "next/link";
import {
  getBarrios,
  getMarketPulse,
  type BarrioWithStats,
  type MarketPulse,
} from "@/lib/api";

export default function DashboardPage() {
  const [barrios, setBarrios] = useState<BarrioWithStats[]>([]);
  const [pulse, setPulse] = useState<MarketPulse | null>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [selectedBarrio, setSelectedBarrio] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getBarrios().then(setBarrios),
      getMarketPulse().then(setPulse),
    ])
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
  }, []);

  const topBarrios = barrios
    .filter((b) => b.median_price_usd_m2 !== null)
    .sort((a, b) => (b.median_price_usd_m2 ?? 0) - (a.median_price_usd_m2 ?? 0))
    .slice(0, 15)
    .map((b) => ({ name: b.name, value: b.median_price_usd_m2, slug: b.slug }));

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
        <div className="h-[500px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Resumen del mercado inmobiliario de CABA</p>
        </div>
        <Link
          href="/map"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
          </svg>
          Ver Mapa
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Listings Activos"
          value={pulse?.active_listings ?? null}
          subtitle="en CABA"
          accent="indigo"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 21v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21m0 0h4.5V3.545M12.75 21h7.5V10.75M2.25 21h1.5m18 0h-18M2.25 9l4.5-1.636M18.75 3l-1.5.545m0 6.205 3 1m1.5.5-1.5-.5M6.75 7.364V3h-3v18m3-13.636 10.5-3.819" />
            </svg>
          }
        />
        <MetricCard
          title="Precio Mediana USD/m2"
          value={pulse?.median_price_usd_m2 ?? null}
          prefix="$"
          suffix="/m2"
          accent="emerald"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          }
        />
        <MetricCard
          title="Nuevos (7d)"
          value={pulse?.new_7d ?? null}
          subtitle="listings esta semana"
          accent="amber"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
            </svg>
          }
        />
        <MetricCard
          title="Dias en Mercado"
          value={pulse?.avg_dom !== null && pulse?.avg_dom !== undefined ? Math.round(pulse.avg_dom) : null}
          suffix=" dias"
          subtitle="promedio"
          accent="rose"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          }
        />
      </div>

      {/* Map + Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Mapa de Precios</h3>
              <p className="text-xs text-slate-400 mt-0.5">Precio mediana USD/m2 por barrio</p>
            </div>
            <Link
              href="/map"
              className="text-xs text-indigo-600 font-medium hover:text-indigo-800 flex items-center gap-1"
            >
              Expandir
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
            </Link>
          </div>
          <div className="h-[300px] md:h-[400px] lg:h-[480px] rounded-xl overflow-hidden">
            <MapContainer onMapReady={handleMapReady}>
              <ChoroplethLayer
                map={map}
                metric="median_price_usd_m2"
                operationType="sale"
                onBarrioClick={setSelectedBarrio}
              />
            </MapContainer>
          </div>
          {selectedBarrio && (
            <div className="mt-3 p-3.5 bg-indigo-50/60 border border-indigo-100 rounded-xl text-sm flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900">
                    {String(selectedBarrio.name || selectedBarrio.barrio_name)}
                  </p>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    {selectedBarrio.metric_value != null && (
                      <span className="font-medium text-indigo-600">
                        ${Number(selectedBarrio.metric_value).toLocaleString("es-AR")}/m2
                      </span>
                    )}
                    {selectedBarrio.listing_count != null && (
                      <span>{String(selectedBarrio.listing_count)} listings</span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedBarrio(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-slate-100 p-5">
          <BarrioBarChart
            data={topBarrios}
            title="Top 15 Barrios por Precio"
            valuePrefix="$"
            valueSuffix="/m2"
          />
        </div>
      </div>
    </div>
  );
}
