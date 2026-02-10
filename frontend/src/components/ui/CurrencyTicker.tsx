"use client";

import { useEffect, useState } from "react";
import { getCurrencyRates, type CurrencyRatesAll } from "@/lib/api";

export default function CurrencyTicker() {
  const [rates, setRates] = useState<CurrencyRatesAll | null>(null);

  useEffect(() => {
    const fetchRates = async () => {
      try {
        const data = await getCurrencyRates();
        setRates(data);
      } catch {
        // silently fail, ticker is non-critical
      }
    };
    fetchRates();
    const interval = setInterval(fetchRates, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (!rates) {
    return (
      <div className="flex items-center gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-7 w-24 bg-slate-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  const items = [
    { label: "Blue", rate: rates.blue, color: "text-indigo-600 bg-indigo-50 border-indigo-100" },
    { label: "Oficial", rate: rates.official, color: "text-slate-600 bg-slate-50 border-slate-100" },
    { label: "MEP", rate: rates.mep, color: "text-emerald-600 bg-emerald-50 border-emerald-100" },
    { label: "CCL", rate: rates.ccl, color: "text-amber-600 bg-amber-50 border-amber-100" },
  ];

  return (
    <div className="flex items-center gap-2">
      {items.map((item) => (
        <div
          key={item.label}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${item.color}`}
        >
          <span className="opacity-70">{item.label}</span>
          {item.rate ? (
            <span className="font-mono font-semibold">
              ${item.rate.sell?.toLocaleString("es-AR") ?? "\u2014"}
            </span>
          ) : (
            <span className="opacity-40">\u2014</span>
          )}
        </div>
      ))}
    </div>
  );
}
