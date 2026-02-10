"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import MetricCard from "@/components/ui/MetricCard";
import PriceTrendChart from "@/components/charts/PriceTrendChart";
import MapContainer from "@/components/map/MapContainer";
import type maplibregl from "maplibre-gl";
import {
  getBarrio,
  getBarrioTrends,
  getListings,
  type BarrioDetail,
  type PriceTrendPoint,
  type ListingItem,
} from "@/lib/api";

export default function BarrioDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [barrio, setBarrio] = useState<BarrioDetail | null>(null);
  const [trends, setTrends] = useState<PriceTrendPoint[]>([]);
  const [listings, setListings] = useState<ListingItem[]>([]);
  const [, setMap] = useState<maplibregl.Map | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getBarrio(slug).then(setBarrio),
      getBarrioTrends(slug).then(setTrends),
      getListings({ barrio_id: undefined, page: 1, per_page: 10 }).then((r) =>
        setListings(r.items)
      ),
    ])
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [slug]);

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
    if (barrio?.centroid_lat && barrio?.centroid_lon) {
      m.flyTo({
        center: [barrio.centroid_lon, barrio.centroid_lat],
        zoom: 14,
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [barrio]);

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-48 bg-slate-200 rounded-lg animate-pulse" />
        <div className="h-4 w-32 bg-slate-100 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-[400px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
          <div className="h-[400px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
        </div>
      </div>
    );
  }

  if (!barrio) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center">
        <p className="text-sm text-rose-700">Barrio no encontrado</p>
        <Link href="/barrios" className="text-sm text-indigo-600 hover:text-indigo-800 mt-2 inline-block">
          Volver a barrios
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/barrios"
          className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-600"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{barrio.name}</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {barrio.comuna_name || `Comuna ${barrio.comuna_id}`}
            {barrio.area_km2 && (
              <span className="text-slate-300 mx-1.5">|</span>
            )}
            {barrio.area_km2 && `${barrio.area_km2} km\u00B2`}
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Mediana USD/m2"
          value={barrio.median_price_usd_m2}
          prefix="$"
          suffix="/m2"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
          accent="indigo"
        />
        <MetricCard
          title="Listings Activos"
          value={barrio.listing_count}
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg>}
          accent="emerald"
        />
        <MetricCard
          title="Dias en Mercado"
          value={barrio.avg_days_on_market !== null ? Math.round(barrio.avg_days_on_market) : null}
          suffix=" dias"
          icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
          accent="amber"
        />
        <MetricCard
          title="Rental Yield"
          value={
            barrio.rental_yield_estimate !== null
              ? (barrio.rental_yield_estimate * 100).toFixed(1)
              : null
          }
          suffix="%"
          accent="rose"
        />
      </div>

      {/* Chart + Map */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-100 p-6">
          <PriceTrendChart data={trends} title="Tendencia Precio/m2" />
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Ubicacion</h3>
          <div className="h-[350px] rounded-xl overflow-hidden">
            <MapContainer
              onMapReady={handleMapReady}
              center={
                barrio.centroid_lon && barrio.centroid_lat
                  ? [barrio.centroid_lon, barrio.centroid_lat]
                  : undefined
              }
              zoom={14}
            />
          </div>
        </div>
      </div>

      {/* Recent Listings */}
      {listings.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">Listings Recientes</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Titulo
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Precio USD
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    m2
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    USD/m2
                  </th>
                </tr>
              </thead>
              <tbody>
                {listings.map((l, idx) => (
                  <tr
                    key={l.id}
                    className={`border-b border-slate-50 hover:bg-slate-50/50 transition-colors ${idx % 2 === 0 ? "" : "bg-slate-25"}`}
                  >
                    <td className="px-4 py-3 text-sm text-slate-800 max-w-xs truncate">
                      {l.title || "Sin titulo"}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {l.property_type}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono font-semibold text-slate-800">
                      {l.price_usd_blue
                        ? `$${l.price_usd_blue.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                        : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {l.surface_total_m2 ?? "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-slate-700">
                      {l.price_usd_m2
                        ? `$${l.price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
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
