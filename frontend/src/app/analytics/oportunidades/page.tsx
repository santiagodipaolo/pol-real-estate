"use client";

import { useState, useEffect } from "react";
import { getOpportunities, type OpportunitiesResponse, type OpportunityItem } from "@/lib/api";

export default function OportunidadesPage() {
  const [data, setData] = useState<OpportunitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operationType, setOperationType] = useState("sale");
  const [threshold, setThreshold] = useState(0.8);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getOpportunities(operationType, threshold, 50)
      .then(setData)
      .catch(() => setError("Error al cargar oportunidades"))
      .finally(() => setLoading(false));
  }, [operationType, threshold]);

  const discountLabel = Math.round((1 - threshold) * 100);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Oportunidades</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Propiedades publicadas por debajo de la mediana de su barrio
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-5 flex flex-wrap items-center gap-5">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Operaci&oacute;n</label>
          <select
            value={operationType}
            onChange={(e) => setOperationType(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
          >
            <option value="sale">Venta</option>
            <option value="rent">Alquiler</option>
          </select>
        </div>

        <div className="flex-1 min-w-[200px] max-w-sm">
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Descuento m&iacute;nimo: <span className="text-indigo-600 font-semibold">{discountLabel}%</span> debajo de mediana
          </label>
          <input
            type="range"
            min="0.6"
            max="0.95"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full accent-indigo-500"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-40%</span>
            <span>-5%</span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {data && !loading && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <div className="text-xs text-slate-500 mb-0.5">Oportunidades encontradas</div>
            <div className="text-2xl font-bold text-slate-900">{data.total}</div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <div className="text-xs text-slate-500 mb-0.5">Descuento promedio</div>
            <div className="text-2xl font-bold text-rose-600">
              {data.avg_discount_pct != null ? `${data.avg_discount_pct.toFixed(1)}%` : "\u2014"}
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <div className="text-xs text-slate-500 mb-0.5">Barrio con m&aacute;s oportunidades</div>
            <div className="text-2xl font-bold text-indigo-600">{data.top_barrio || "\u2014"}</div>
          </div>
        </div>
      )}

      {/* Loading / Error */}
      {loading && (
        <div className="text-center py-12 text-sm text-slate-400">Buscando oportunidades...</div>
      )}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Results Grid */}
      {data && !loading && data.items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((item: OpportunityItem) => (
            <div
              key={item.id}
              className="bg-white rounded-2xl border border-slate-100 p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-slate-900 truncate">
                    {item.title || "Sin t\u00edtulo"}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {item.barrio_name} &middot; {item.property_type}
                  </p>
                </div>
                <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700 flex-shrink-0">
                  -{item.discount_pct.toFixed(0)}%
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 mb-3">
                <div>
                  <div className="text-[10px] text-slate-500">Precio</div>
                  <div className="text-sm font-semibold text-slate-900 font-mono">
                    {item.price_usd_blue != null
                      ? `USD ${item.price_usd_blue.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                      : "\u2014"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">USD/m\u00b2</div>
                  <div className="text-sm font-semibold text-slate-900 font-mono">
                    {item.price_usd_m2 != null
                      ? `$${item.price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                      : "\u2014"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Superficie</div>
                  <div className="text-sm font-medium text-slate-700">
                    {item.surface_total_m2 != null ? `${item.surface_total_m2} m\u00b2` : "\u2014"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Mediana barrio</div>
                  <div className="text-sm font-medium text-slate-700 font-mono">
                    ${item.median_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </div>
                </div>
              </div>

              {/* Discount bar */}
              <div className="mb-3">
                <div className="flex items-center gap-2 text-[10px] text-slate-500 mb-1">
                  <span>Propiedad</span>
                  <span className="flex-1" />
                  <span>Mediana</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full relative overflow-hidden">
                  <div
                    className="absolute left-0 top-0 h-full bg-rose-400 rounded-full"
                    style={{
                      width: `${Math.min(100, ((item.price_usd_m2 || 0) / item.median_price_usd_m2) * 100)}%`,
                    }}
                  />
                </div>
              </div>

              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1.5 w-full px-3 py-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-xs font-medium transition-colors"
                >
                  Ver publicaci&oacute;n
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                  </svg>
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {data && !loading && data.items.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 p-12 flex flex-col items-center justify-center text-center">
          <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Sin oportunidades</h3>
          <p className="text-xs text-slate-500 max-w-md">
            No se encontraron propiedades con un descuento de {discountLabel}% o m&aacute;s respecto a la mediana.
            Intente reducir el umbral de descuento.
          </p>
        </div>
      )}
    </div>
  );
}
