"use client";

import { useState, useCallback } from "react";
import MapContainer from "@/components/map/MapContainer";
import ChoroplethLayer from "@/components/map/ChoroplethLayer";
import GlobalFilters, { type FilterState } from "@/components/ui/GlobalFilters";
import type maplibregl from "maplibre-gl";

export default function MapPage() {
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    operationType: "sale",
    propertyType: "",
    currency: "usd_blue",
  });
  const [selectedBarrio, setSelectedBarrio] = useState<Record<string, unknown> | null>(null);
  const [metric, setMetric] = useState("median_price_usd_m2");

  const handleMapReady = useCallback((m: maplibregl.Map) => {
    setMap(m);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      {/* Controls */}
      <div className="flex items-center gap-4 pb-4">
        <GlobalFilters onFilterChange={setFilters} />
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="median_price_usd_m2">Precio Mediana/m2</option>
          <option value="avg_price_usd_m2">Precio Promedio/m2</option>
          <option value="listing_count">Cantidad Listings</option>
          <option value="avg_days_on_market">Dias en Mercado</option>
          <option value="rental_yield_estimate">Rental Yield</option>
        </select>
      </div>

      {/* Full-screen map */}
      <div className="flex-1 relative rounded-xl overflow-hidden shadow-sm border border-gray-100">
        <MapContainer onMapReady={handleMapReady} zoom={12}>
          <ChoroplethLayer
            map={map}
            metric={metric}
            operationType={filters.operationType || "sale"}
            onBarrioClick={setSelectedBarrio}
          />
        </MapContainer>

        {/* Info panel */}
        {selectedBarrio && (
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-4 min-w-[240px] z-10">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-gray-900">
                {String(selectedBarrio.name || selectedBarrio.barrio_name)}
              </h3>
              <button
                onClick={() => setSelectedBarrio(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                x
              </button>
            </div>
            <div className="space-y-1 text-sm">
              {selectedBarrio.metric_value !== null && (
                <p>
                  <span className="text-gray-500">Valor:</span>{" "}
                  <span className="font-semibold">
                    ${Number(selectedBarrio.metric_value).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </span>
                </p>
              )}
              {selectedBarrio.listing_count != null && (
                <p>
                  <span className="text-gray-500">Listings:</span>{" "}
                  {String(selectedBarrio.listing_count)}
                </p>
              )}
              {selectedBarrio.comuna_name != null && (
                <p>
                  <span className="text-gray-500">Comuna:</span>{" "}
                  {String(selectedBarrio.comuna_name)}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
