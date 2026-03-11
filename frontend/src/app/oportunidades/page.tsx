"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function scoreColor(score: number) {
  if (score >= 75) return "text-emerald-600 bg-emerald-50";
  if (score >= 55) return "text-blue-600 bg-blue-50";
  if (score >= 35) return "text-amber-600 bg-amber-50";
  return "text-red-600 bg-red-50";
}

function verdictLabel(verdict: string) {
  const map: Record<string, string> = {
    oportunidad: "Oportunidad",
    precio_justo: "Precio justo",
    caro: "Caro",
    sobrepreciado: "Sobrepreciado",
  };
  return map[verdict] || verdict;
}

function verdictColor(verdict: string) {
  const map: Record<string, string> = {
    oportunidad: "bg-emerald-100 text-emerald-700",
    precio_justo: "bg-blue-100 text-blue-700",
    caro: "bg-amber-100 text-amber-700",
    sobrepreciado: "bg-red-100 text-red-700",
  };
  return map[verdict] || "bg-slate-100 text-slate-700";
}

interface ScoredItem {
  listing_id: string;
  url: string | null;
  title: string | null;
  barrio_name: string | null;
  property_type: string;
  surface_total_m2: number;
  rooms: number | null;
  listed_price_usd: number;
  listed_price_usd_m2: number;
  estimated_price_usd: number;
  estimated_price_usd_m2: number;
  estimated_low: number;
  estimated_high: number;
  score: number;
  discount_pct: number;
  verdict: string;
}

interface AnalyzeResult {
  url: string;
  title: string | null;
  barrio_name: string | null;
  property_type: string;
  operation_type: string;
  surface_total_m2: number | null;
  rooms: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  garages: number | null;
  listed_price_usd: number | null;
  listed_price_usd_m2: number | null;
  estimated_price_usd: number | null;
  estimated_price_usd_m2: number | null;
  estimated_low: number | null;
  estimated_high: number | null;
  score: number | null;
  discount_pct: number | null;
  verdict: string | null;
  confidence: string | null;
}

export default function OportunidadesPage() {
  const [activeTab, setActiveTab] = useState<"scored" | "analyze">("analyze");

  // Analyze URL state
  const [urlInput, setUrlInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResult | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // Scored list state
  const [scored, setScored] = useState<ScoredItem[]>([]);
  const [scoredLoading, setScoredLoading] = useState(false);
  const [scoredLoaded, setScoredLoaded] = useState(false);
  const [scoredStats, setScoredStats] = useState<{ total: number; avg_score: number; best_barrio: string | null }>({ total: 0, avg_score: 0, best_barrio: null });

  async function handleAnalyze() {
    if (!urlInput.trim()) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalyzeResult(null);
    try {
      const res = await fetch(`${API_BASE}/opportunities/analyze-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data: AnalyzeResult = await res.json();
      setAnalyzeResult(data);
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setAnalyzing(false);
    }
  }

  async function loadScored() {
    setScoredLoading(true);
    try {
      const res = await fetch(`${API_BASE}/opportunities/scored?min_score=0&limit=100`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setScored(data.items);
      setScoredStats({ total: data.total, avg_score: data.avg_score, best_barrio: data.best_barrio });
      setScoredLoaded(true);
    } catch {
      // ignore
    } finally {
      setScoredLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Oportunidades</h1>
        <p className="text-sm text-slate-500 mt-1">Score ML: compara precio publicado vs valuación estimada</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab("analyze")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            activeTab === "analyze" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          Analizar URL
        </button>
        <button
          onClick={() => { setActiveTab("scored"); if (!scoredLoaded) loadScored(); }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            activeTab === "scored" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          Ranking
        </button>
      </div>

      {/* Analyze URL Tab */}
      {activeTab === "analyze" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Analizar propiedad de Zonaprop</h2>
            <div className="flex gap-3">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                placeholder="https://www.zonaprop.com.ar/propiedades/..."
                className="flex-1 px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
              />
              <button
                onClick={handleAnalyze}
                disabled={analyzing || !urlInput.trim()}
                className="px-6 py-3 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {analyzing ? "Analizando..." : "Analizar"}
              </button>
            </div>
            {analyzeError && (
              <p className="mt-3 text-sm text-red-600">{analyzeError}</p>
            )}
          </div>

          {analyzeResult && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              {/* Header with score */}
              <div className="p-6 border-b border-slate-100">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">{analyzeResult.title || "Propiedad"}</h3>
                    <p className="text-sm text-slate-500 mt-1">
                      {analyzeResult.barrio_name && `${analyzeResult.barrio_name} · `}
                      {analyzeResult.property_type}
                      {analyzeResult.surface_total_m2 && ` · ${analyzeResult.surface_total_m2} m²`}
                      {analyzeResult.rooms && ` · ${analyzeResult.rooms} amb`}
                    </p>
                  </div>
                  {analyzeResult.score != null && (
                    <div className="text-right">
                      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl ${scoreColor(analyzeResult.score)}`}>
                        <span className="text-2xl font-bold">{analyzeResult.score.toFixed(0)}</span>
                        <span className="text-xs font-medium">/100</span>
                      </div>
                      {analyzeResult.verdict && (
                        <div className={`mt-2 inline-block px-3 py-1 rounded-full text-xs font-medium ${verdictColor(analyzeResult.verdict)}`}>
                          {verdictLabel(analyzeResult.verdict)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Price comparison */}
              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Precio publicado</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">
                    {analyzeResult.listed_price_usd ? formatUSD(analyzeResult.listed_price_usd) : "N/A"}
                  </p>
                  {analyzeResult.listed_price_usd_m2 && (
                    <p className="text-sm text-slate-500">{formatUSD(analyzeResult.listed_price_usd_m2)}/m²</p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Valuación estimada</p>
                  <p className="text-2xl font-bold text-indigo-600 mt-1">
                    {analyzeResult.estimated_price_usd ? formatUSD(analyzeResult.estimated_price_usd) : "N/A"}
                  </p>
                  {analyzeResult.estimated_price_usd_m2 && (
                    <p className="text-sm text-slate-500">{formatUSD(analyzeResult.estimated_price_usd_m2)}/m²</p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Diferencia</p>
                  {analyzeResult.discount_pct != null ? (
                    <>
                      <p className={`text-2xl font-bold mt-1 ${analyzeResult.discount_pct > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {analyzeResult.discount_pct > 0 ? "+" : ""}{analyzeResult.discount_pct.toFixed(1)}%
                      </p>
                      <p className="text-sm text-slate-500">
                        {analyzeResult.discount_pct > 0 ? "por debajo" : "por encima"} del estimado
                      </p>
                    </>
                  ) : (
                    <p className="text-2xl font-bold text-slate-400 mt-1">N/A</p>
                  )}
                </div>
              </div>

              {/* Range bar */}
              {analyzeResult.estimated_low && analyzeResult.estimated_high && analyzeResult.listed_price_usd && (
                <div className="px-6 pb-6">
                  <div className="bg-slate-50 rounded-xl p-4">
                    <p className="text-xs font-medium text-slate-500 mb-3">Rango de valuación (p10 - p90)</p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-slate-500 font-medium">{formatUSD(analyzeResult.estimated_low)}</span>
                      <div className="flex-1 h-3 bg-slate-200 rounded-full relative overflow-hidden">
                        <div
                          className="absolute inset-y-0 bg-indigo-200 rounded-full"
                          style={{
                            left: "0%",
                            right: "0%",
                          }}
                        />
                        {/* Marker for listed price */}
                        {(() => {
                          const range = analyzeResult.estimated_high! - analyzeResult.estimated_low!;
                          const pos = range > 0
                            ? Math.max(0, Math.min(100, ((analyzeResult.listed_price_usd! - analyzeResult.estimated_low!) / range) * 100))
                            : 50;
                          return (
                            <div
                              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-slate-900 rounded-full border-2 border-white shadow"
                              style={{ left: `${pos}%` }}
                              title={`Precio publicado: ${formatUSD(analyzeResult.listed_price_usd!)}`}
                            />
                          );
                        })()}
                      </div>
                      <span className="text-slate-500 font-medium">{formatUSD(analyzeResult.estimated_high)}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-2 text-center">
                      El punto negro indica el precio publicado
                    </p>
                  </div>
                </div>
              )}

              {/* Details grid */}
              <div className="px-6 pb-6">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {[
                    { label: "Superficie", value: analyzeResult.surface_total_m2 ? `${analyzeResult.surface_total_m2} m²` : null },
                    { label: "Ambientes", value: analyzeResult.rooms },
                    { label: "Dormitorios", value: analyzeResult.bedrooms },
                    { label: "Baños", value: analyzeResult.bathrooms },
                    { label: "Cocheras", value: analyzeResult.garages },
                  ].map((d) => (
                    <div key={d.label} className="bg-slate-50 rounded-lg p-3">
                      <p className="text-xs text-slate-500">{d.label}</p>
                      <p className="text-sm font-semibold text-slate-900">{d.value ?? "-"}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Scored Ranking Tab */}
      {activeTab === "scored" && (
        <div className="space-y-4">
          {scoredLoading && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
              <p className="text-slate-500">Calculando scores para todos los listings...</p>
            </div>
          )}

          {scoredLoaded && (
            <>
              {/* Stats bar */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 font-medium">Total analizados</p>
                  <p className="text-2xl font-bold text-slate-900">{scoredStats.total}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 font-medium">Score promedio</p>
                  <p className="text-2xl font-bold text-indigo-600">{scoredStats.avg_score.toFixed(1)}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 font-medium">Mejor barrio</p>
                  <p className="text-lg font-bold text-slate-900">{scoredStats.best_barrio || "-"}</p>
                </div>
              </div>

              {/* Table */}
              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50/50">
                        <th className="text-left px-4 py-3 font-medium text-slate-500">Score</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-500">Propiedad</th>
                        <th className="text-left px-4 py-3 font-medium text-slate-500">Barrio</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-500">Publicado</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-500">Estimado</th>
                        <th className="text-right px-4 py-3 font-medium text-slate-500">Diff</th>
                        <th className="text-center px-4 py-3 font-medium text-slate-500">Veredicto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scored.map((item) => (
                        <tr key={item.listing_id} className="border-b border-slate-50 hover:bg-slate-50/50">
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg text-sm font-bold ${scoreColor(item.score)}`}>
                              {item.score.toFixed(0)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium text-slate-900 truncate max-w-[200px]">
                                {item.url ? (
                                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600">
                                    {item.title || `${item.property_type} ${item.surface_total_m2}m²`}
                                  </a>
                                ) : (
                                  item.title || `${item.property_type} ${item.surface_total_m2}m²`
                                )}
                              </p>
                              <p className="text-xs text-slate-500">{item.property_type} · {item.surface_total_m2}m² · {item.rooms || "?"} amb</p>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-slate-600">{item.barrio_name || "-"}</td>
                          <td className="px-4 py-3 text-right font-mono text-slate-900">{formatUSD(item.listed_price_usd_m2)}/m²</td>
                          <td className="px-4 py-3 text-right font-mono text-indigo-600">{formatUSD(item.estimated_price_usd_m2)}/m²</td>
                          <td className="px-4 py-3 text-right">
                            <span className={`font-mono font-medium ${item.discount_pct > 0 ? "text-emerald-600" : "text-red-600"}`}>
                              {item.discount_pct > 0 ? "+" : ""}{item.discount_pct.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${verdictColor(item.verdict)}`}>
                              {verdictLabel(item.verdict)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
