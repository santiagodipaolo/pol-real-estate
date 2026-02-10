"use client";

import { useState, useMemo, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import MetricCard from "@/components/ui/MetricCard";

interface FormState {
  propertyPriceUsd: string;
  downPaymentPct: string;
  loanTermYears: string;
  annualRate: string;
  uvaValue: string;
  blueRate: string;
  annualInflation: string;
}

const defaultForm: FormState = {
  propertyPriceUsd: "100000",
  downPaymentPct: "20",
  loanTermYears: "20",
  annualRate: "5.5",
  uvaValue: "",
  blueRate: "",
  annualInflation: "50",
};

interface ScheduleRow {
  month: number;
  paymentArs: number;
  paymentUva: number;
  capitalArs: number;
  interestArs: number;
  remainingUva: number;
}

const inputClass =
  "w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400";

export default function UvaCalculatorPage() {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [fetchingUva, setFetchingUva] = useState(false);

  // Fetch UVA + blue rate on mount
  useEffect(() => {
    setFetchingUva(true);

    // Fetch UVA value from BCRA
    fetch("https://api.bcra.gob.ar/estadisticas/v3.0/Monetarias/UVA", {
      headers: { Accept: "application/json" },
    })
      .then((r) => r.json())
      .then((data) => {
        const results = data?.results;
        if (Array.isArray(results) && results.length > 0) {
          const latest = results[results.length - 1];
          setForm((prev) => ({ ...prev, uvaValue: String(latest.valor || latest.v || "") }));
        }
      })
      .catch(() => {});

    // Fetch blue rate from DolarAPI
    fetch("https://dolarapi.com/v1/dolares/blue")
      .then((r) => r.json())
      .then((data) => {
        if (data?.venta) {
          setForm((prev) => ({ ...prev, blueRate: String(data.venta) }));
        }
      })
      .catch(() => {})
      .finally(() => setFetchingUva(false));
  }, []);

  const updateField = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  // Compute amortization
  const result = useMemo(() => {
    const priceUsd = Number(form.propertyPriceUsd) || 0;
    const downPct = Number(form.downPaymentPct) / 100 || 0;
    const years = Number(form.loanTermYears) || 0;
    const tna = Number(form.annualRate) / 100 || 0;
    const uva = Number(form.uvaValue) || 0;
    const blue = Number(form.blueRate) || 0;
    const annualInflation = Number(form.annualInflation) / 100 || 0;

    if (!priceUsd || !years || !tna || !uva || !blue) return null;

    const loanUsd = priceUsd * (1 - downPct);
    const loanArs = loanUsd * blue;
    const loanUva = loanArs / uva;
    const monthlyRate = tna / 12;
    const totalMonths = years * 12;

    // French payment in UVAs
    const paymentUva =
      (loanUva * monthlyRate * Math.pow(1 + monthlyRate, totalMonths)) /
      (Math.pow(1 + monthlyRate, totalMonths) - 1);

    const monthlyInflation = Math.pow(1 + annualInflation, 1 / 12) - 1;

    // Build schedule
    const schedule: ScheduleRow[] = [];
    let remaining = loanUva;
    let currentUvaValue = uva;

    for (let m = 1; m <= totalMonths; m++) {
      // UVA value grows with inflation
      currentUvaValue *= 1 + monthlyInflation;

      const interestUva = remaining * monthlyRate;
      const capitalUva = paymentUva - interestUva;
      remaining -= capitalUva;

      const paymentArs = paymentUva * currentUvaValue;
      const capitalArs = capitalUva * currentUvaValue;
      const interestArs = interestUva * currentUvaValue;

      schedule.push({
        month: m,
        paymentArs: Math.round(paymentArs),
        paymentUva: Math.round(paymentUva * 100) / 100,
        capitalArs: Math.round(capitalArs),
        interestArs: Math.round(interestArs),
        remainingUva: Math.max(0, Math.round(remaining * 100) / 100),
      });
    }

    const firstPayment = schedule[0]?.paymentArs || 0;
    const lastPayment = schedule[schedule.length - 1]?.paymentArs || 0;
    const totalPaid = schedule.reduce((sum, r) => sum + r.paymentArs, 0);

    return {
      loanUsd,
      loanArs,
      loanUva: Math.round(loanUva),
      paymentUva: Math.round(paymentUva * 100) / 100,
      firstPayment,
      lastPayment,
      totalPaid,
      schedule,
    };
  }, [form]);

  // Chart data (sample every 12 months)
  const chartData = useMemo(() => {
    if (!result) return [];
    return result.schedule
      .filter((r) => r.month % 6 === 1 || r.month === result.schedule.length)
      .map((r) => ({
        label: `Mes ${r.month}`,
        cuota: r.paymentArs,
      }));
  }, [result]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Calculadora UVA</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Simule un cr&eacute;dito hipotecario UVA con proyecci&oacute;n de cuotas ajustadas por inflaci&oacute;n
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-6 space-y-4">
            <h2 className="text-sm font-semibold text-slate-900">Par&aacute;metros del Cr&eacute;dito</h2>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Precio Propiedad</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">USD</span>
                <input type="number" step="any" value={form.propertyPriceUsd} onChange={(e) => updateField("propertyPriceUsd", e.target.value)} className={`${inputClass} pl-12`} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Anticipo</label>
              <div className="relative">
                <input type="number" step="any" value={form.downPaymentPct} onChange={(e) => updateField("downPaymentPct", e.target.value)} className={`${inputClass} pr-8`} />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">%</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Plazo</label>
              <div className="relative">
                <input type="number" step="1" value={form.loanTermYears} onChange={(e) => updateField("loanTermYears", e.target.value)} className={`${inputClass} pr-14`} />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">a&ntilde;os</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Tasa Nominal Anual (TNA)</label>
              <div className="relative">
                <input type="number" step="any" value={form.annualRate} onChange={(e) => updateField("annualRate", e.target.value)} className={`${inputClass} pr-8`} />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">%</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Valor UVA Actual
                {fetchingUva && <span className="text-indigo-400 ml-1">(cargando...)</span>}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">ARS</span>
                <input type="number" step="any" value={form.uvaValue} onChange={(e) => updateField("uvaValue", e.target.value)} className={`${inputClass} pl-12`} />
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Fuente: BCRA (editable)</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">D&oacute;lar Blue</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">ARS</span>
                <input type="number" step="any" value={form.blueRate} onChange={(e) => updateField("blueRate", e.target.value)} className={`${inputClass} pl-12`} />
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Fuente: DolarAPI (editable)</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Inflaci&oacute;n Anual Estimada</label>
              <div className="relative">
                <input type="number" step="any" value={form.annualInflation} onChange={(e) => updateField("annualInflation", e.target.value)} className={`${inputClass} pr-8`} />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">%</span>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Para proyecci&oacute;n de cuotas en ARS</p>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {result ? (
            <>
              {/* Key Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  title="Cuota Inicial"
                  value={result.firstPayment.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  prefix="ARS "
                  subtitle="Primera cuota mensual"
                  accent="indigo"
                />
                <MetricCard
                  title="Cuota Final Proyectada"
                  value={result.lastPayment.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  prefix="ARS "
                  subtitle={`Mes ${result.schedule.length}`}
                  accent="amber"
                />
                <MetricCard
                  title="Cuota en UVAs"
                  value={result.paymentUva.toLocaleString("es-AR")}
                  suffix=" UVAs"
                  subtitle="Constante durante todo el cr\u00e9dito"
                  accent="emerald"
                />
                <MetricCard
                  title="Total a Pagar"
                  value={Math.round(result.totalPaid / 1000000).toLocaleString("es-AR")}
                  prefix="ARS "
                  suffix="M"
                  subtitle="Monto total proyectado"
                  accent="rose"
                />
              </div>

              {/* Loan Summary */}
              <div className="bg-white rounded-2xl border border-slate-100 p-5">
                <h3 className="text-sm font-semibold text-slate-900 mb-3">Resumen del Cr&eacute;dito</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500">Monto USD</div>
                    <div className="font-semibold text-slate-900 font-mono">
                      USD {result.loanUsd.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Monto ARS</div>
                    <div className="font-semibold text-slate-900 font-mono">
                      ARS {result.loanArs.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Monto UVAs</div>
                    <div className="font-semibold text-slate-900 font-mono">
                      {result.loanUva.toLocaleString("es-AR")} UVAs
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Anticipo</div>
                    <div className="font-semibold text-slate-900 font-mono">
                      USD {(Number(form.propertyPriceUsd) * Number(form.downPaymentPct) / 100).toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart */}
              {chartData.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-100 p-4 md:p-5">
                  <h3 className="text-sm font-semibold text-slate-900 mb-4">
                    Proyecci&oacute;n de Cuota Mensual (ARS)
                  </h3>
                  <div className="h-[250px] md:h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="cuotaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis
                        dataKey="label"
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: "#94a3b8" }}
                        tickFormatter={(v: number) => {
                          if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
                          if (v >= 1000) return `${(v / 1000).toFixed(0)}k`;
                          return String(v);
                        }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          border: "none",
                          borderRadius: "12px",
                          fontSize: "12px",
                          color: "#e2e8f0",
                        }}
                        formatter={(value: number | undefined) => [
                          value != null ? `ARS ${value.toLocaleString("es-AR")}` : "\u2014",
                          "Cuota",
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="cuota"
                        stroke="#6366f1"
                        strokeWidth={2}
                        fill="url(#cuotaGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 p-12 flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
                <svg className="w-7 h-7 text-indigo-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 15.75V18m-7.5-6.75V18m15-8.25v.75a.75.75 0 0 1-.75.75H1.5a.75.75 0 0 1-.75-.75v-.75m20.25 0V6.375c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v3.375m20.25 0h-20.25" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-slate-900 mb-1">Calculadora UVA</h3>
              <p className="text-xs text-slate-500 max-w-md">
                Complete los par&aacute;metros del cr&eacute;dito para ver la simulaci&oacute;n de cuotas UVA.
                Los valores de UVA y d&oacute;lar blue se cargan autom&aacute;ticamente.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
