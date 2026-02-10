"use client";

import { useEffect, useState, useCallback, use } from "react";
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
    return <div className="animate-pulse text-gray-400">Cargando barrio...</div>;
  }

  if (!barrio) {
    return <div className="text-red-500">Barrio no encontrado</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{barrio.name}</h1>
        <p className="text-sm text-gray-500">
          {barrio.comuna_name || `Comuna ${barrio.comuna_id}`}
          {barrio.area_km2 && ` | ${barrio.area_km2} km2`}
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Mediana USD/m2"
          value={barrio.median_price_usd_m2}
          prefix="$"
          suffix="/m2"
        />
        <MetricCard
          title="Listings Activos"
          value={barrio.listing_count}
        />
        <MetricCard
          title="Dias en Mercado"
          value={barrio.avg_days_on_market !== null ? Math.round(barrio.avg_days_on_market) : null}
          suffix=" dias"
        />
        <MetricCard
          title="Rental Yield"
          value={
            barrio.rental_yield_estimate !== null
              ? `${(barrio.rental_yield_estimate * 100).toFixed(1)}%`
              : null
          }
        />
      </div>

      {/* Chart + Map */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <PriceTrendChart data={trends} title="Tendencia Precio/m2" />
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h3 className="text-lg font-semibold mb-3">Ubicacion</h3>
          <div className="h-[350px]">
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
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h3 className="text-lg font-semibold mb-3">Listings Recientes</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Titulo
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Tipo
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Precio USD
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    m2
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    USD/m2
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {listings.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm max-w-xs truncate">
                      {l.title || "Sin titulo"}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-500">
                      {l.property_type}
                    </td>
                    <td className="px-4 py-2 text-sm font-mono">
                      {l.price_usd_blue
                        ? `$${l.price_usd_blue.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-sm">
                      {l.surface_total_m2 ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-sm font-mono">
                      {l.price_usd_m2
                        ? `$${l.price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                        : "—"}
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
