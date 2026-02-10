"use client";

import { useEffect, useState, useCallback } from "react";
import MetricCard from "@/components/ui/MetricCard";
import MapContainer from "@/components/map/MapContainer";
import ChoroplethLayer from "@/components/map/ChoroplethLayer";
import BarrioBarChart from "@/components/charts/BarrioBarChart";
import type maplibregl from "maplibre-gl";
import {
  getBarrios,
  getMarketPulse,
  getCurrencyRates,
  type BarrioWithStats,
  type MarketPulse,
  type CurrencyRatesAll,
} from "@/lib/api";

export default function DashboardPage() {
  const [barrios, setBarrios] = useState<BarrioWithStats[]>([]);
  const [pulse, setPulse] = useState<MarketPulse | null>(null);
  const [rates, setRates] = useState<CurrencyRatesAll | null>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [selectedBarrio, setSelectedBarrio] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    getBarrios().then(setBarrios).catch(() => {});
    getMarketPulse().then(setPulse).catch(() => {});
    getCurrencyRates().then(setRates).catch(() => {});
  }, []);

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
  }, []);

  const topBarrios = barrios
    .filter((b) => b.median_price_usd_m2 !== null)
    .sort((a, b) => (b.median_price_usd_m2 ?? 0) - (a.median_price_usd_m2 ?? 0))
    .slice(0, 15)
    .map((b) => ({ name: b.name, value: b.median_price_usd_m2, slug: b.slug }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        {rates?.blue && (
          <div className="text-sm text-gray-500">
            USD Blue: ${rates.blue.sell?.toLocaleString("es-AR")}
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Listings Activos"
          value={pulse?.active_listings ?? null}
        />
        <MetricCard
          title="Precio Mediana USD/m2"
          value={pulse?.median_price_usd_m2 ?? null}
          prefix="$"
          suffix="/m2"
        />
        <MetricCard
          title="Nuevos (7d)"
          value={pulse?.new_7d ?? null}
          subtitle="listings esta semana"
        />
        <MetricCard
          title="Dias en Mercado (avg)"
          value={pulse?.avg_dom !== null && pulse?.avg_dom !== undefined ? Math.round(pulse.avg_dom) : null}
          suffix=" dias"
        />
      </div>

      {/* Map + Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h3 className="text-lg font-semibold mb-3">Mapa de Precios - CABA</h3>
          <div className="h-[500px]">
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
            <div className="mt-3 p-3 bg-blue-50 rounded-lg text-sm">
              <strong>{String(selectedBarrio.name || selectedBarrio.barrio_name)}</strong>
              {selectedBarrio.metric_value != null && (
                <span className="ml-2">
                  ${Number(selectedBarrio.metric_value).toLocaleString("es-AR")}/m2
                </span>
              )}
              {selectedBarrio.listing_count != null && (
                <span className="ml-2 text-gray-500">
                  ({String(selectedBarrio.listing_count)} listings)
                </span>
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
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
