"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import MapContainer from "@/components/map/MapContainer";
import ChoroplethLayer from "@/components/map/ChoroplethLayer";
import HeatmapLayer from "@/components/map/HeatmapLayer";
import type maplibregl from "maplibre-gl";

type ViewMode = "choropleth" | "heatmap";

const METRIC_LABELS: Record<string, string> = {
  median_price_usd_m2: "Mediana USD/m\u00b2",
  avg_price_usd_m2: "Promedio USD/m\u00b2",
  listing_count: "Publicaciones",
  avg_days_on_market: "D\u00edas en mercado",
  rental_yield_estimate: "Rental Yield",
};

function formatValue(value: number | null | undefined, metric: string): string {
  if (value == null) return "\u2014";
  if (metric === "listing_count") return String(Math.round(value));
  if (metric === "rental_yield_estimate") return `${value.toFixed(1)}%`;
  if (metric === "avg_days_on_market") return `${Math.round(value)} d\u00edas`;
  return `$${value.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`;
}

export default function MapPage() {
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [operationType, setOperationType] = useState("sale");
  const [selectedBarrio, setSelectedBarrio] = useState<Record<string, unknown> | null>(null);
  const [hoveredBarrio, setHoveredBarrio] = useState<Record<string, unknown> | null>(null);
  const [metric, setMetric] = useState("median_price_usd_m2");
  const [propertyType, setPropertyType] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("choropleth");

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
  }, []);

  // Escape to deselect
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedBarrio(null);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const selectedName = selectedBarrio
    ? String(selectedBarrio.name || selectedBarrio.barrio_name || "")
    : "";
  const selectedSlug = selectedBarrio
    ? String(selectedBarrio.slug || "")
    : "";

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      {/* Controls Bar */}
      <div className="flex items-center justify-between pb-3">
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-800/60 backdrop-blur-sm rounded-xl border border-slate-700/50 p-0.5">
            <button
              onClick={() => { setViewMode("choropleth"); setSelectedBarrio(null); }}
              className={`px-3.5 py-1.5 rounded-[10px] text-xs font-medium transition-all ${
                viewMode === "choropleth"
                  ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/25"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Coropletas
            </button>
            <button
              onClick={() => { setViewMode("heatmap"); setSelectedBarrio(null); }}
              className={`px-3.5 py-1.5 rounded-[10px] text-xs font-medium transition-all ${
                viewMode === "heatmap"
                  ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/25"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Mapa de Calor
            </button>
          </div>

          {/* Operation Type */}
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-700/50 bg-slate-800/60 backdrop-blur-sm text-xs font-medium text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50"
          >
            <option value="sale">Venta</option>
            <option value="rent">Alquiler</option>
          </select>

          {/* Property Type Filter */}
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-700/50 bg-slate-800/60 backdrop-blur-sm text-xs font-medium text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50"
          >
            <option value="">Todos los tipos</option>
            <option value="Departamento">Departamento</option>
            <option value="Casa">Casa</option>
            <option value="PH">PH</option>
          </select>

          {/* Metric Selector (only for choropleth) */}
          {viewMode === "choropleth" && (
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-700/50 bg-slate-800/60 backdrop-blur-sm text-xs font-medium text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50"
            >
              <option value="median_price_usd_m2">Precio Mediana/m\u00b2</option>
              <option value="avg_price_usd_m2">Precio Promedio/m\u00b2</option>
              <option value="listing_count">Cantidad Listings</option>
              <option value="avg_days_on_market">Dias en Mercado</option>
              <option value="rental_yield_estimate">Rental Yield</option>
            </select>
          )}
        </div>

        {/* Legend */}
        {viewMode === "heatmap" && (
          <div className="flex items-center gap-2.5 text-[11px] text-slate-400">
            <span>Menor</span>
            <div className="flex h-2.5 rounded-full overflow-hidden" style={{
              background: "linear-gradient(to right, #0a143c, #1450b4, #00b4dc, #50faa0, #b4ff50, #ffe628, #ffb414, #ff781e, #f03232, #c8143c)",
              width: "140px",
            }} />
            <span>Mayor</span>
          </div>
        )}

        {viewMode === "choropleth" && (
          <div className="flex items-center gap-2.5 text-[11px] text-slate-400">
            <span>Bajo</span>
            <div className="flex h-2.5 rounded-full overflow-hidden" style={{
              background: "linear-gradient(to right, #0d1b2a, #1b3a5c, #1a6b8a, #1d9a8c, #3ec47e, #7ddf64, #c5e84d, #ffe23b, #ffb627)",
              width: "140px",
            }} />
            <span>Alto</span>
          </div>
        )}
      </div>

      {/* Map */}
      <div className="flex-1 relative rounded-2xl overflow-hidden border border-slate-700/50 shadow-2xl shadow-black/20">
        <MapContainer onMapReady={handleMapReady} zoom={12}>
          {viewMode === "choropleth" ? (
            <ChoroplethLayer
              map={map}
              metric={metric}
              operationType={operationType}
              propertyType={propertyType || undefined}
              onBarrioClick={setSelectedBarrio}
              onBarrioHover={setHoveredBarrio}
            />
          ) : (
            <HeatmapLayer
              map={map}
              operationType={operationType}
              propertyType={propertyType || undefined}
              onBarrioHover={setHoveredBarrio}
            />
          )}
        </MapContainer>

        {/* Selected Barrio Detail Panel */}
        {selectedBarrio && viewMode === "choropleth" && (
          <div className="absolute top-4 right-4 bg-slate-900/85 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-4 w-[280px] z-10 animate-in">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-white text-sm truncate pr-2">
                {selectedName}
              </h3>
              <button
                onClick={() => setSelectedBarrio(null)}
                className="text-slate-500 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded-lg flex-shrink-0"
                title="Cerrar (Esc)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-2">
              {/* Main metric */}
              <div className="bg-slate-800/60 rounded-xl p-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">
                  {METRIC_LABELS[metric] || metric}
                </div>
                <div className="text-lg font-bold text-emerald-400">
                  {formatValue(
                    selectedBarrio.metric_value != null ? Number(selectedBarrio.metric_value) : null,
                    metric,
                  )}
                </div>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-2 gap-2">
                {selectedBarrio.listing_count != null && (
                  <div className="bg-slate-800/40 rounded-lg px-3 py-2">
                    <div className="text-[10px] text-slate-500">Publicaciones</div>
                    <div className="text-sm font-semibold text-slate-200">{String(selectedBarrio.listing_count)}</div>
                  </div>
                )}
                {selectedBarrio.comuna_name != null && (
                  <div className="bg-slate-800/40 rounded-lg px-3 py-2">
                    <div className="text-[10px] text-slate-500">Comuna</div>
                    <div className="text-sm font-semibold text-slate-200">{String(selectedBarrio.comuna_name)}</div>
                  </div>
                )}
              </div>

              {/* Link to barrio detail */}
              {selectedSlug && (
                <Link
                  href={`/barrios/${selectedSlug}`}
                  className="flex items-center justify-center gap-2 w-full mt-1 px-3 py-2 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 hover:text-indigo-200 rounded-xl text-xs font-medium transition-all border border-indigo-500/20"
                >
                  <span>Ver barrio completo</span>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                  </svg>
                </Link>
              )}
            </div>

            <div className="mt-2 text-[10px] text-slate-600 text-center">
              Esc para cerrar
            </div>
          </div>
        )}

        {/* Heatmap mode footer */}
        {viewMode === "heatmap" && (
          <div className="absolute bottom-4 left-4 bg-slate-900/70 backdrop-blur-xl rounded-xl px-3.5 py-2.5 shadow-lg border border-slate-700/50 z-10">
            <p className="text-xs font-medium text-slate-200">
              Precio USD/m\u00b2
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {operationType === "sale" ? "Precios de venta" : "Precios de alquiler"}
            </p>
          </div>
        )}

        {/* Bottom-right hover mini-badge (both modes) */}
        {hoveredBarrio && !selectedBarrio && (
          <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur-xl rounded-xl px-3 py-2 shadow-lg border border-slate-700/50 z-10 pointer-events-none">
            <div className="text-xs font-semibold text-white">
              {String(hoveredBarrio.name || hoveredBarrio.barrio_name || "")}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
