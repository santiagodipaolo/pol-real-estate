"use client";

import { useState, useCallback } from "react";
import MapContainer from "@/components/map/MapContainer";
import ChoroplethLayer from "@/components/map/ChoroplethLayer";
import HeatmapLayer from "@/components/map/HeatmapLayer";
import type maplibregl from "maplibre-gl";

type ViewMode = "choropleth" | "heatmap";

export default function MapPage() {
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [operationType, setOperationType] = useState("sale");
  const [selectedBarrio, setSelectedBarrio] = useState<Record<string, unknown> | null>(null);
  const [metric, setMetric] = useState("median_price_usd_m2");
  const [viewMode, setViewMode] = useState<ViewMode>("choropleth");

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      {/* Controls Bar */}
      <div className="flex items-center justify-between pb-4">
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-white rounded-xl border border-slate-200 p-0.5">
            <button
              onClick={() => setViewMode("choropleth")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                viewMode === "choropleth"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Coropletas
            </button>
            <button
              onClick={() => setViewMode("heatmap")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                viewMode === "heatmap"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Mapa de Calor
            </button>
          </div>

          {/* Operation Type */}
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
          >
            <option value="sale">Venta</option>
            <option value="rent">Alquiler</option>
          </select>

          {/* Metric Selector (only for choropleth) */}
          {viewMode === "choropleth" && (
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
            >
              <option value="median_price_usd_m2">Precio Mediana/m2</option>
              <option value="avg_price_usd_m2">Precio Promedio/m2</option>
              <option value="listing_count">Cantidad Listings</option>
              <option value="avg_days_on_market">Dias en Mercado</option>
              <option value="rental_yield_estimate">Rental Yield</option>
            </select>
          )}
        </div>

        {/* Legend */}
        {viewMode === "heatmap" && (
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span>Menor precio</span>
            <div className="flex h-3 rounded-full overflow-hidden">
              <div className="w-6 bg-indigo-200" />
              <div className="w-6 bg-indigo-400" />
              <div className="w-6 bg-amber-400" />
              <div className="w-6 bg-red-400" />
              <div className="w-6 bg-red-600" />
            </div>
            <span>Mayor precio</span>
          </div>
        )}
      </div>

      {/* Map */}
      <div className="flex-1 relative rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
        <MapContainer onMapReady={handleMapReady} zoom={12}>
          {viewMode === "choropleth" ? (
            <ChoroplethLayer
              map={map}
              metric={metric}
              operationType={operationType}
              onBarrioClick={setSelectedBarrio}
            />
          ) : (
            <HeatmapLayer
              map={map}
              operationType={operationType}
            />
          )}
        </MapContainer>

        {/* Selected Barrio Panel */}
        {selectedBarrio && viewMode === "choropleth" && (
          <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-sm rounded-2xl shadow-lg border border-slate-100 p-4 min-w-[260px] z-10">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-900 text-sm">
                {String(selectedBarrio.name || selectedBarrio.barrio_name)}
              </h3>
              <button
                onClick={() => setSelectedBarrio(null)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-0.5"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="space-y-2">
              {selectedBarrio.metric_value !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Valor</span>
                  <span className="text-sm font-bold text-indigo-600">
                    ${Number(selectedBarrio.metric_value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </span>
                </div>
              )}
              {selectedBarrio.listing_count != null && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Listings</span>
                  <span className="text-sm font-semibold text-slate-700">
                    {String(selectedBarrio.listing_count)}
                  </span>
                </div>
              )}
              {selectedBarrio.comuna_name != null && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Comuna</span>
                  <span className="text-sm text-slate-700">
                    {String(selectedBarrio.comuna_name)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Heatmap mode label */}
        {viewMode === "heatmap" && (
          <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-xl px-3 py-2 shadow-sm border border-slate-100 z-10">
            <p className="text-xs font-medium text-slate-600">
              Mapa de calor - Precio USD/m2
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Basado en {operationType === "sale" ? "precios de venta" : "precios de alquiler"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
