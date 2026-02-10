"use client";

import { useEffect, useState, useCallback } from "react";
import GlobalFilters, { type FilterState } from "@/components/ui/GlobalFilters";
import PriceTrendChart from "@/components/charts/PriceTrendChart";
import MetricCard from "@/components/ui/MetricCard";
import { getPriceTrends, type PriceTrendPoint } from "@/lib/api";

export default function PriceTrendsPage() {
  const [data, setData] = useState<PriceTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    operationType: "sale",
    propertyType: "",
    currency: "usd_blue",
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getPriceTrends(
        filters.operationType || undefined,
        filters.currency || undefined
      );
      setData(result);
    } catch (err) {
      setError("Error al cargar datos de tendencia de precios.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filters.operationType, filters.currency]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleFilterChange = useCallback((next: FilterState) => {
    setFilters(next);
  }, []);

  // Compute stats from the data
  const latestPoint = data.length > 0 ? data[data.length - 1] : null;
  const firstPoint = data.length > 0 ? data[0] : null;
  const priceChange =
    latestPoint && firstPoint && firstPoint.price_m2 > 0
      ? ((latestPoint.price_m2 - firstPoint.price_m2) / firstPoint.price_m2) * 100
      : null;
  const avgPrice =
    data.length > 0
      ? Math.round(data.reduce((sum, d) => sum + d.price_m2, 0) / data.length)
      : null;
  const maxPrice =
    data.length > 0
      ? Math.max(...data.map((d) => d.price_m2))
      : null;
  const minPrice =
    data.length > 0
      ? Math.min(...data.map((d) => d.price_m2))
      : null;
  const totalListings =
    data.length > 0
      ? data.reduce((sum, d) => sum + (d.listing_count ?? 0), 0)
      : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tendencia de Precios</h1>
          <p className="text-sm text-gray-500 mt-1">
            Evolucion del precio por m2 en Buenos Aires (CABA)
          </p>
        </div>
        <GlobalFilters onFilterChange={handleFilterChange} />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
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
          <PriceTrendChart
            data={data}
            title={`Precio/m2 - ${filters.operationType === "rent" ? "Alquiler" : "Venta"} (${filters.currency.replace("_", " ").toUpperCase()})`}
          />
        )}
      </div>

      {/* Stats Section */}
      {!loading && !error && data.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Resumen Estadistico</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
              title="Precio Actual"
              value={latestPoint?.price_m2 ?? null}
              prefix="$"
              suffix="/m2"
              delta={priceChange}
              deltaLabel="vs inicio del periodo"
            />
            <MetricCard
              title="Precio Promedio"
              value={avgPrice}
              prefix="$"
              suffix="/m2"
            />
            <MetricCard
              title="Maximo"
              value={maxPrice ? Math.round(maxPrice) : null}
              prefix="$"
              suffix="/m2"
            />
            <MetricCard
              title="Minimo"
              value={minPrice ? Math.round(minPrice) : null}
              prefix="$"
              suffix="/m2"
            />
            <MetricCard
              title="Listings Totales"
              value={totalListings}
              subtitle="en el periodo"
            />
          </div>
        </div>
      )}

      {/* Period info */}
      {!loading && !error && data.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="flex flex-wrap items-center gap-6 text-sm text-gray-500">
            <div>
              <span className="font-medium text-gray-700">Periodo:</span>{" "}
              {firstPoint ? new Date(firstPoint.date).toLocaleDateString("es-AR") : "—"}{" "}
              -{" "}
              {latestPoint ? new Date(latestPoint.date).toLocaleDateString("es-AR") : "—"}
            </div>
            <div>
              <span className="font-medium text-gray-700">Puntos de datos:</span>{" "}
              {data.length}
            </div>
            <div>
              <span className="font-medium text-gray-700">Moneda:</span>{" "}
              {filters.currency.replace("_", " ").toUpperCase()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
