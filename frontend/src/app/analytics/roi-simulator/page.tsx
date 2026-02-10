"use client";

import { useState } from "react";
import MetricCard from "@/components/ui/MetricCard";
import { simulateROI, type ROISimulationRequest, type ROISimulationResult } from "@/lib/api";

interface FormState {
  purchase_price_usd: string;
  monthly_rent_usd: string;
  monthly_expenses_usd: string;
  vacancy_rate: string;
  annual_appreciation: string;
  closing_costs_pct: string;
  holding_period_years: string;
  discount_rate: string;
}

const defaultForm: FormState = {
  purchase_price_usd: "120000",
  monthly_rent_usd: "600",
  monthly_expenses_usd: "100",
  vacancy_rate: "5",
  annual_appreciation: "3",
  closing_costs_pct: "5",
  holding_period_years: "10",
  discount_rate: "8",
};

const fields: { key: keyof FormState; label: string; hint: string; prefix?: string; suffix?: string }[] = [
  {
    key: "purchase_price_usd",
    label: "Precio de Compra",
    hint: "Valor total en USD",
    prefix: "USD ",
  },
  {
    key: "monthly_rent_usd",
    label: "Alquiler Mensual",
    hint: "Ingreso mensual estimado",
    prefix: "USD ",
  },
  {
    key: "monthly_expenses_usd",
    label: "Gastos Mensuales",
    hint: "Expensas, impuestos, mantenimiento",
    prefix: "USD ",
  },
  {
    key: "vacancy_rate",
    label: "Tasa de Vacancia",
    hint: "Porcentaje de tiempo sin alquilar",
    suffix: "%",
  },
  {
    key: "annual_appreciation",
    label: "Apreciacion Anual",
    hint: "Estimacion de aumento del valor",
    suffix: "%",
  },
  {
    key: "closing_costs_pct",
    label: "Costos de Cierre",
    hint: "Escritura, comisiones, sellados",
    suffix: "%",
  },
  {
    key: "holding_period_years",
    label: "Periodo de Tenencia",
    hint: "Horizonte de inversion",
    suffix: " anios",
  },
  {
    key: "discount_rate",
    label: "Tasa de Descuento",
    hint: "Para calculo de VAN/NPV",
    suffix: "%",
  },
];

const inputClass =
  "w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400";

export default function ROISimulatorPage() {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [result, setResult] = useState<ROISimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: ROISimulationRequest = {
      purchase_price_usd: Number(form.purchase_price_usd),
      monthly_rent_usd: Number(form.monthly_rent_usd),
      monthly_expenses_usd: Number(form.monthly_expenses_usd) || undefined,
      vacancy_rate: Number(form.vacancy_rate) / 100 || undefined,
      annual_appreciation: Number(form.annual_appreciation) / 100 || undefined,
      closing_costs_pct: Number(form.closing_costs_pct) / 100 || undefined,
      holding_period_years: Number(form.holding_period_years) || undefined,
      discount_rate: Number(form.discount_rate) / 100 || undefined,
    };

    try {
      const res = await simulateROI(payload);
      setResult(res);
    } catch (err) {
      setError("Error al ejecutar la simulacion. Verifique los datos ingresados.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(defaultForm);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Simulador de ROI</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Calcule el retorno de inversion para una propiedad en Buenos Aires
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-1">
          <form
            onSubmit={handleSubmit}
            className="bg-white rounded-2xl border border-slate-100 p-6 space-y-4"
          >
            <h2 className="text-sm font-semibold text-slate-900">Parametros</h2>

            {fields.map((field) => (
              <div key={field.key}>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  {field.label}
                </label>
                <div className="relative">
                  {field.prefix && (
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                      {field.prefix}
                    </span>
                  )}
                  <input
                    type="number"
                    step="any"
                    value={form[field.key]}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    className={`${inputClass} ${
                      field.prefix ? "pl-14" : ""
                    } ${field.suffix ? "pr-12" : ""}`}
                  />
                  {field.suffix && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                      {field.suffix}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">{field.hint}</p>
              </div>
            ))}

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-indigo-600 text-white py-2.5 px-4 rounded-xl text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Calculando..." : "Calcular ROI"}
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Reset
              </button>
            </div>
          </form>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 text-sm text-rose-700">
              {error}
            </div>
          )}

          {result && (
            <>
              {/* Main Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  title="TIR (IRR)"
                  value={
                    result.irr != null
                      ? (result.irr * 100).toFixed(2)
                      : null
                  }
                  suffix="%"
                  subtitle="Tasa Interna de Retorno"
                  icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" /></svg>}
                  accent="emerald"
                />
                <MetricCard
                  title="VAN (NPV)"
                  value={
                    result.npv != null
                      ? Math.round(result.npv)
                      : null
                  }
                  prefix="USD "
                  subtitle="Valor Actual Neto"
                  accent="indigo"
                />
                <MetricCard
                  title="Payback"
                  value={
                    result.payback_years != null
                      ? result.payback_years.toFixed(1)
                      : null
                  }
                  suffix=" anios"
                  subtitle="Periodo de recupero"
                  accent="amber"
                />
                <MetricCard
                  title="Cash on Cash"
                  value={
                    result.cash_on_cash_return != null
                      ? (result.cash_on_cash_return * 100).toFixed(2)
                      : null
                  }
                  suffix="%"
                  subtitle="Retorno sobre efectivo"
                  accent="rose"
                />
              </div>

              {/* Secondary Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Inversion Total"
                  value={Math.round(result.total_investment)}
                  prefix="USD "
                />
                <MetricCard
                  title="Ingreso Neto Anual"
                  value={Math.round(result.annual_net_income)}
                  prefix="USD "
                />
                <MetricCard
                  title="Cap Rate"
                  value={
                    result.cap_rate != null
                      ? (result.cap_rate * 100).toFixed(2)
                      : null
                  }
                  suffix="%"
                />
                <MetricCard
                  title="Yield Bruto"
                  value={
                    result.gross_rental_yield != null
                      ? (result.gross_rental_yield * 100).toFixed(2)
                      : null
                  }
                  suffix="%"
                />
              </div>

              {/* Summary */}
              <div className="bg-white rounded-2xl border border-slate-100 p-6">
                <h3 className="text-sm font-semibold text-slate-900 mb-4">
                  Resumen de la Inversion
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Precio de compra:</span>
                      <span className="font-medium text-slate-900 font-mono">
                        USD {Number(form.purchase_price_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Costos de cierre ({form.closing_costs_pct}%):</span>
                      <span className="font-medium text-slate-900 font-mono">
                        USD{" "}
                        {(
                          Number(form.purchase_price_usd) *
                          (Number(form.closing_costs_pct) / 100)
                        ).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-slate-100 pt-3">
                      <span className="text-slate-700 font-semibold">Inversion total:</span>
                      <span className="font-bold text-slate-900 font-mono">
                        USD {result.total_investment.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Alquiler mensual:</span>
                      <span className="font-medium text-slate-900 font-mono">
                        USD {Number(form.monthly_rent_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Gastos mensuales:</span>
                      <span className="font-medium text-rose-600 font-mono">
                        -USD {Number(form.monthly_expenses_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Vacancia ({form.vacancy_rate}%):</span>
                      <span className="font-medium text-rose-600 font-mono">
                        -USD{" "}
                        {(
                          Number(form.monthly_rent_usd) *
                          (Number(form.vacancy_rate) / 100)
                        ).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                        /mes
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-slate-100 pt-3">
                      <span className="text-slate-700 font-semibold">Ingreso neto anual:</span>
                      <span className="font-bold text-emerald-700 font-mono">
                        USD {result.annual_net_income.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="bg-white rounded-2xl border border-slate-100 p-12 flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
                <svg
                  className="w-7 h-7 text-indigo-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008Zm0 2.25h.008v.008H8.25V13.5Zm0 2.25h.008v.008H8.25v-.008Zm0 2.25h.008v.008H8.25V18Zm2.498-6.75h.007v.008h-.007v-.008Zm0 2.25h.007v.008h-.007V13.5Zm0 2.25h.007v.008h-.007v-.008Zm0 2.25h.007v.008h-.007V18Zm2.504-6.75h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V13.5Zm0 2.25h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V18Zm2.498-6.75h.008v.008h-.008v-.008ZM18 13.5h.008v.008H18V13.5Zm-2.25 0h.008v.008h-.008V13.5Zm0-2.25h.008v.008h-.008v-.008ZM15.75 18h.008v.008h-.008V18Z"
                  />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-slate-900 mb-1">
                Simule su inversion
              </h3>
              <p className="text-xs text-slate-500 max-w-md">
                Complete los parametros en el formulario y presione &quot;Calcular ROI&quot;
                para ver el analisis detallado de retorno de inversion.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
