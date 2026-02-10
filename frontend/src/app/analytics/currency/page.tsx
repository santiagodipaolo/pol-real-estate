"use client";

import { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import MetricCard from "@/components/ui/MetricCard";
import {
  getCurrencyHistory,
  getCurrencyRates,
  type CurrencyHistory,
  type CurrencyRatesAll,
} from "@/lib/api";

const rateTypes = [
  { value: "blue", label: "Blue" },
  { value: "official", label: "Oficial" },
  { value: "mep", label: "MEP" },
  { value: "ccl", label: "CCL" },
];

const selectClass =
  "px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400";

function getDefaultFromDate(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 6);
  return d.toISOString().split("T")[0];
}

function getDefaultToDate(): string {
  return new Date().toISOString().split("T")[0];
}

export default function CurrencyPage() {
  const [rateType, setRateType] = useState("blue");
  const [fromDate, setFromDate] = useState(getDefaultFromDate);
  const [toDate, setToDate] = useState(getDefaultToDate);
  const [history, setHistory] = useState<CurrencyHistory | null>(null);
  const [rates, setRates] = useState<CurrencyRatesAll | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCurrencyHistory(rateType, fromDate, toDate);
      setHistory(result);
    } catch (err) {
      setError("Error al cargar historial de cotizaciones.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [rateType, fromDate, toDate]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    getCurrencyRates().then(setRates).catch(() => {});
  }, []);

  const blueSell = rates?.blue?.sell ?? null;
  const oficialSell = rates?.official?.sell ?? null;
  const brecha =
    blueSell != null && oficialSell != null && oficialSell > 0
      ? ((blueSell - oficialSell) / oficialSell) * 100
      : null;

  const chartData =
    history?.points.map((p) => ({
      date: p.date,
      compra: p.buy,
      venta: p.sell,
    })) ?? [];

  if (loading && !rates) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-56 bg-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-100 animate-pulse" />
          ))}
        </div>
        <div className="h-[460px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Cotizacion del Dolar</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Historial de cotizaciones y brecha cambiaria
        </p>
      </div>

      {/* Current Rates */}
      {rates && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Blue (Venta)"
            value={rates.blue?.sell ?? null}
            prefix="$"
            subtitle={
              rates.blue?.recorded_at
                ? new Date(rates.blue.recorded_at).toLocaleDateString("es-AR")
                : undefined
            }
            icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>}
            accent="indigo"
          />
          <MetricCard
            title="Oficial (Venta)"
            value={rates.official?.sell ?? null}
            prefix="$"
            accent="slate"
          />
          <MetricCard
            title="MEP (Venta)"
            value={rates.mep?.sell ?? null}
            prefix="$"
            accent="emerald"
          />
          <MetricCard
            title="CCL (Venta)"
            value={rates.ccl?.sell ?? null}
            prefix="$"
            accent="amber"
          />
          <MetricCard
            title="Brecha Blue/Oficial"
            value={brecha != null ? brecha.toFixed(1) : null}
            suffix="%"
            delta={brecha}
            deltaLabel="brecha actual"
            accent="rose"
          />
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-slate-100 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-[11px] text-slate-500 mb-1 font-semibold uppercase tracking-wider">
              Tipo de cambio
            </label>
            <select
              value={rateType}
              onChange={(e) => setRateType(e.target.value)}
              className={selectClass}
            >
              {rateTypes.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-slate-500 mb-1 font-semibold uppercase tracking-wider">
              Desde
            </label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className={selectClass}
            />
          </div>
          <div>
            <label className="block text-[11px] text-slate-500 mb-1 font-semibold uppercase tracking-wider">
              Hasta
            </label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className={selectClass}
            />
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">
          Historial - Dolar {rateTypes.find((r) => r.value === rateType)?.label}
        </h2>
        {loading ? (
          <div className="flex items-center justify-center h-80 text-slate-400 text-sm">
            Cargando datos...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-80 text-rose-500 text-sm">
            {error}
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-80 text-slate-400 text-sm">
            Sin datos disponibles para el periodo seleccionado
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return `${d.getDate()}/${d.getMonth() + 1}`;
                }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                tickFormatter={(v) => `$${(v as number).toLocaleString()}`}
                domain={["auto", "auto"]}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                  fontSize: "12px",
                  padding: "8px 12px",
                }}
                formatter={(value) => [
                  `$${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`,
                ]}
                labelFormatter={(label) =>
                  new Date(label).toLocaleDateString("es-AR")
                }
                cursor={{ stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 }}
              />
              <Legend
                wrapperStyle={{ fontSize: "11px", color: "#64748b" }}
              />
              <Line
                type="monotone"
                dataKey="compra"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: "#10b981", stroke: "white", strokeWidth: 2 }}
                name="Compra"
              />
              <Line
                type="monotone"
                dataKey="venta"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: "#6366f1", stroke: "white", strokeWidth: 2 }}
                name="Venta"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Brecha Calculator */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-1">Calculadora de Brecha Cambiaria</h2>
        <p className="text-xs text-slate-500 mb-5">
          La brecha se calcula como: (Blue Venta - Oficial Venta) / Oficial Venta x 100
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-50 rounded-xl">
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Dolar Blue (Venta)</p>
            <p className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
              {blueSell != null
                ? `$${blueSell.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                : "\u2014"}
            </p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl">
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Dolar Oficial (Venta)</p>
            <p className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
              {oficialSell != null
                ? `$${oficialSell.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                : "\u2014"}
            </p>
          </div>
          <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100">
            <p className="text-xs text-indigo-600 font-semibold uppercase tracking-wider">Brecha</p>
            <p className="text-2xl font-bold text-indigo-900 mt-2 tracking-tight">
              {brecha != null ? `${brecha.toFixed(1)}%` : "\u2014"}
            </p>
            <p className="text-[10px] text-indigo-500 mt-1">
              {brecha != null && brecha > 50
                ? "Brecha elevada"
                : brecha != null && brecha > 20
                  ? "Brecha moderada"
                  : brecha != null
                    ? "Brecha baja"
                    : ""}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
