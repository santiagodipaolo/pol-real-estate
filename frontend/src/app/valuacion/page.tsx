"use client";

import { useState } from "react";
import {
  estimateValuation,
  ValuationRequest,
  ValuationResponse,
} from "@/lib/api";

const BARRIOS = [
  "Palermo", "Belgrano", "Recoleta", "Caballito", "Núñez", "Villa Urquiza",
  "Colegiales", "Villa Crespo", "Almagro", "San Telmo", "Puerto Madero",
  "Retiro", "Balvanera", "Flores", "Monserrat", "San Nicolás", "Barracas",
  "La Boca", "Boedo", "Parque Patricios", "Chacarita", "Devoto", "Saavedra",
  "Liniers", "Mataderos", "Constitución", "Once", "Parque Chas",
  "Villa del Parque", "Villa Luro", "Vélez Sársfield", "Agronomía",
  "Paternal", "Monte Castro", "Versalles", "Villa Pueyrredón",
  "Villa Real", "Villa General Mitre", "Villa Soldati", "Villa Lugano",
  "Villa Riachuelo", "Nueva Pompeya", "Parque Avellaneda",
  "Floresta", "Coghlan", "Belgrano R", "Las Cañitas",
];

const PROPERTY_TYPES = [
  "Departamento", "Casa", "PH", "Local", "Oficina", "Terreno",
];

function formatUSD(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function ConfidenceBadge({ level }: { level: string }) {
  const colors = {
    high: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    low: "bg-red-500/15 text-red-400 border-red-500/30",
  };
  const labels = { high: "Alta", medium: "Media", low: "Baja" };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${colors[level as keyof typeof colors] || colors.low}`}>
      {labels[level as keyof typeof labels] || level}
    </span>
  );
}

export default function ValuacionPage() {
  const [form, setForm] = useState<ValuationRequest>({
    surface_total_m2: 60,
    rooms: 2,
    bedrooms: 1,
    bathrooms: 1,
    garages: 0,
    age_years: 20,
    expenses_ars: 80000,
    property_type: "Departamento",
    barrio_name: "Palermo",
  });
  const [result, setResult] = useState<ValuationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await estimateValuation(form);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al calcular valuación");
    } finally {
      setLoading(false);
    }
  };

  const update = (key: keyof ValuationRequest, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Motor de Valuación</h1>
        <p className="text-sm text-slate-400 mt-1">
          Estimá el valor de mercado de una propiedad con inteligencia artificial
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="lg:col-span-2 space-y-4">
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Datos de la propiedad</h2>

            {/* Barrio */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Barrio</label>
              <select
                value={form.barrio_name || ""}
                onChange={(e) => update("barrio_name", e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                {BARRIOS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            {/* Property Type */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Tipo</label>
              <select
                value={form.property_type}
                onChange={(e) => update("property_type", e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                {PROPERTY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Surface */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Superficie total (m²)</label>
                <input
                  type="number"
                  value={form.surface_total_m2}
                  onChange={(e) => update("surface_total_m2", Number(e.target.value))}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={1}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Sup. cubierta (m²)</label>
                <input
                  type="number"
                  value={form.surface_covered_m2 || ""}
                  onChange={(e) => update("surface_covered_m2", Number(e.target.value) || 0)}
                  placeholder="Opcional"
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
            </div>

            {/* Rooms */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Ambientes</label>
                <input
                  type="number"
                  value={form.rooms || ""}
                  onChange={(e) => update("rooms", Number(e.target.value))}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={1}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Dormitorios</label>
                <input
                  type="number"
                  value={form.bedrooms || ""}
                  onChange={(e) => update("bedrooms", Number(e.target.value))}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={0}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Baños</label>
                <input
                  type="number"
                  value={form.bathrooms || ""}
                  onChange={(e) => update("bathrooms", Number(e.target.value))}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={1}
                />
              </div>
            </div>

            {/* Extras */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Cocheras</label>
                <input
                  type="number"
                  value={form.garages || 0}
                  onChange={(e) => update("garages", Number(e.target.value))}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={0}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Antigüedad</label>
                <input
                  type="number"
                  value={form.age_years || ""}
                  onChange={(e) => update("age_years", Number(e.target.value))}
                  placeholder="Años"
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={0}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Expensas</label>
                <input
                  type="number"
                  value={form.expenses_ars || ""}
                  onChange={(e) => update("expenses_ars", Number(e.target.value))}
                  placeholder="ARS/mes"
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  min={0}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
            >
              {loading ? "Calculando..." : "Calcular valuación"}
            </button>
          </div>
        </form>

        {/* Result */}
        <div className="lg:col-span-3">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Main result card */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Valuación estimada</h2>
                  <ConfidenceBadge level={result.confidence} />
                </div>

                <div className="text-center py-4">
                  <p className="text-4xl font-bold text-white">{formatUSD(result.price_usd)}</p>
                  <p className="text-sm text-slate-400 mt-2">
                    Rango: {formatUSD(result.price_usd_low)} — {formatUSD(result.price_usd_high)}
                  </p>
                </div>

                {/* Price bar visualization */}
                <div className="mt-4 px-2">
                  <div className="relative h-3 bg-slate-700/50 rounded-full overflow-hidden">
                    {/* Range bar */}
                    <div
                      className="absolute h-full bg-indigo-500/30 rounded-full"
                      style={{
                        left: `${((result.price_usd_low / result.price_usd_high) * 100) * 0.9}%`,
                        right: `${(1 - 0.9) * 100}%`,
                      }}
                    />
                    {/* Estimate marker */}
                    <div
                      className="absolute top-0 h-full w-1 bg-indigo-400 rounded-full"
                      style={{
                        left: `${(result.price_usd / result.price_usd_high) * 90}%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between mt-1.5 text-[11px] text-slate-500">
                    <span>{formatUSD(result.price_usd_low)}</span>
                    <span>{formatUSD(result.price_usd_high)}</span>
                  </div>
                </div>
              </div>

              {/* Details grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">USD/m²</p>
                  <p className="text-lg font-bold text-white">{formatUSD(result.price_usd_m2)}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatUSD(result.price_usd_m2_low)} - {formatUSD(result.price_usd_m2_high)}
                  </p>
                </div>
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">Superficie</p>
                  <p className="text-lg font-bold text-white">{result.surface_total_m2} m²</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{form.property_type}</p>
                </div>
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">Barrio</p>
                  <p className="text-lg font-bold text-white">{form.barrio_name}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{form.rooms} amb, {form.bedrooms} dorm</p>
                </div>
              </div>

              {/* Disclaimer */}
              <p className="text-[11px] text-slate-600 text-center">
                Valuación basada en {248} propiedades analizadas. Los precios son estimativos y no constituyen una tasación formal.
              </p>
            </div>
          )}

          {!result && !error && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-500/10 flex items-center justify-center">
                <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0 0 12 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 0 1-2.031.352 5.988 5.988 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971Zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 0 1-2.031.352 5.989 5.989 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971Z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-300">Estimá el valor de una propiedad</h3>
              <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
                Completá los datos de la propiedad y nuestro modelo de ML calculará un precio estimado basado en datos reales del mercado.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
