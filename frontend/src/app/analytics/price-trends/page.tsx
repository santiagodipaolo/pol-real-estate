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
    data.length > 0 ? Math.max(...data.map((d) => d.price_m2)) : null;
  const minPrice =
    data.length > 0 ? Math.min(...data.map((d) => d.price_m2)) : null;
  const totalListings =
    data.length > 0
      ? data.reduce((sum, d) => sum + (d.listing_count ?? 0), 0)
      : null;

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-56 bg-slate-200 rounded-lg animate-pulse" />
        <div className="h-[420px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tendencia de Precios</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Evolucion del precio por m2 en Buenos Aires (CABA)
          </p>
        </div>
        <GlobalFilters onFilterChange={handleFilterChange} />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6">
        {error ? (
          <div className="flex items-center justify-center h-80 text-rose-500 text-sm">
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
      {!error && data.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Resumen Estadistico</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
              title="Precio Actual"
              value={latestPoint?.price_m2 ?? null}
              prefix="$"
              suffix="/m2"
              delta={priceChange}
              deltaLabel="vs inicio"
              icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
              accent="indigo"
            />
            <MetricCard
              title="Precio Promedio"
              value={avgPrice}
              prefix="$"
              suffix="/m2"
              accent="slate"
            />
            <MetricCard
              title="Maximo"
              value={maxPrice ? Math.round(maxPrice) : null}
              prefix="$"
              suffix="/m2"
              accent="emerald"
            />
            <MetricCard
              title="Minimo"
              value={minPrice ? Math.round(minPrice) : null}
              prefix="$"
              suffix="/m2"
              accent="amber"
            />
            <MetricCard
              title="Listings Totales"
              value={totalListings}
              subtitle="en el periodo"
              accent="slate"
            />
          </div>
        </div>
      )}

      {/* Period info */}
      {!error && data.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-4">
          <div className="flex flex-wrap items-center gap-6 text-xs text-slate-500">
            <div>
              <span className="font-semibold text-slate-700">Periodo:</span>{" "}
              {firstPoint ? new Date(firstPoint.date).toLocaleDateString("es-AR") : "\u2014"}{" "}
              -{" "}
              {latestPoint ? new Date(latestPoint.date).toLocaleDateString("es-AR") : "\u2014"}
            </div>
            <div>
              <span className="font-semibold text-slate-700">Puntos de datos:</span>{" "}
              {data.length}
            </div>
            <div>
              <span className="font-semibold text-slate-700">Moneda:</span>{" "}
              {filters.currency.replace("_", " ").toUpperCase()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
