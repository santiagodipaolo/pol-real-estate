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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Simulador de ROI</h1>
        <p className="text-sm text-gray-500 mt-1">
          Calcule el retorno de inversion para una propiedad en Buenos Aires
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-1">
          <form
            onSubmit={handleSubmit}
            className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4"
          >
            <h2 className="text-lg font-semibold text-gray-900">Parametros</h2>

            {fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {field.label}
                </label>
                <div className="relative">
                  {field.prefix && (
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
                      {field.prefix}
                    </span>
                  )}
                  <input
                    type="number"
                    step="any"
                    value={form[field.key]}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    className={`w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      field.prefix ? "pl-14" : ""
                    } ${field.suffix ? "pr-12" : ""}`}
                  />
                  {field.suffix && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
                      {field.suffix}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">{field.hint}</p>
              </div>
            ))}

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-2.5 px-4 rounded-lg text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Calculando..." : "Calcular ROI"}
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                Reset
              </button>
            </div>
          </form>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
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
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Resumen de la Inversion
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Precio de compra:</span>
                      <span className="font-medium text-gray-900">
                        USD {Number(form.purchase_price_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Costos de cierre ({form.closing_costs_pct}%):</span>
                      <span className="font-medium text-gray-900">
                        USD{" "}
                        {(
                          Number(form.purchase_price_usd) *
                          (Number(form.closing_costs_pct) / 100)
                        ).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-gray-100 pt-2">
                      <span className="text-gray-700 font-medium">Inversion total:</span>
                      <span className="font-bold text-gray-900">
                        USD {result.total_investment.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Alquiler mensual:</span>
                      <span className="font-medium text-gray-900">
                        USD {Number(form.monthly_rent_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Gastos mensuales:</span>
                      <span className="font-medium text-red-600">
                        -USD {Number(form.monthly_expenses_usd).toLocaleString("es-AR")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Vacancia ({form.vacancy_rate}%):</span>
                      <span className="font-medium text-red-600">
                        -USD{" "}
                        {(
                          Number(form.monthly_rent_usd) *
                          (Number(form.vacancy_rate) / 100)
                        ).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                        /mes
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-gray-100 pt-2">
                      <span className="text-gray-700 font-medium">Ingreso neto anual:</span>
                      <span className="font-bold text-green-700">
                        USD {result.annual_net_income.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-blue-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Simule su inversion
              </h3>
              <p className="text-sm text-gray-500 max-w-md">
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
