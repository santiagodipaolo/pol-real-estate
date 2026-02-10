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

  // Brecha calculation
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cotizacion del Dolar</h1>
        <p className="text-sm text-gray-500 mt-1">
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
          />
          <MetricCard
            title="Oficial (Venta)"
            value={rates.official?.sell ?? null}
            prefix="$"
            subtitle={
              rates.official?.recorded_at
                ? new Date(rates.official.recorded_at).toLocaleDateString("es-AR")
                : undefined
            }
          />
          <MetricCard
            title="MEP (Venta)"
            value={rates.mep?.sell ?? null}
            prefix="$"
          />
          <MetricCard
            title="CCL (Venta)"
            value={rates.ccl?.sell ?? null}
            prefix="$"
          />
          <MetricCard
            title="Brecha Blue/Oficial"
            value={brecha != null ? brecha.toFixed(1) : null}
            suffix="%"
            delta={brecha}
            deltaLabel="brecha actual"
          />
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1 font-medium">
              Tipo de cambio
            </label>
            <select
              value={rateType}
              onChange={(e) => setRateType(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {rateTypes.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1 font-medium">
              Desde
            </label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1 font-medium">
              Hasta
            </label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold mb-4">
          Historial - Dolar {rateTypes.find((r) => r.value === rateType)?.label}
        </h2>
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
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-80 text-gray-400">
            Sin datos disponibles para el periodo seleccionado
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return `${d.getDate()}/${d.getMonth() + 1}`;
                }}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `$${(v as number).toLocaleString()}`}
                domain={["auto", "auto"]}
              />
              <Tooltip
                formatter={(value) => [
                  `$${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`,
                ]}
                labelFormatter={(label) =>
                  new Date(label).toLocaleDateString("es-AR")
                }
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="compra"
                stroke="#16a34a"
                strokeWidth={2}
                dot={false}
                name="Compra"
              />
              <Line
                type="monotone"
                dataKey="venta"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                name="Venta"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Brecha Calculator */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold mb-4">Calculadora de Brecha Cambiaria</h2>
        <p className="text-sm text-gray-500 mb-4">
          La brecha se calcula como: (Blue Venta - Oficial Venta) / Oficial Venta x 100
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 font-medium">Dolar Blue (Venta)</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {blueSell != null
                ? `$${blueSell.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                : "—"}
            </p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 font-medium">Dolar Oficial (Venta)</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {oficialSell != null
                ? `$${oficialSell.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`
                : "—"}
            </p>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-700 font-medium">Brecha</p>
            <p className="text-2xl font-bold text-blue-900 mt-1">
              {brecha != null ? `${brecha.toFixed(1)}%` : "—"}
            </p>
            <p className="text-xs text-blue-600 mt-1">
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
