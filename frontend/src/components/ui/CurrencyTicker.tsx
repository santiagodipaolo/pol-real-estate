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
      <div className="flex items-center gap-4 text-sm text-gray-400 animate-pulse">
        Cargando cotizaciones...
      </div>
    );
  }

  const items = [
    { label: "Blue", rate: rates.blue },
    { label: "Oficial", rate: rates.official },
    { label: "MEP", rate: rates.mep },
    { label: "CCL", rate: rates.ccl },
  ];

  return (
    <div className="flex items-center gap-6 text-sm">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-gray-400 font-medium">{item.label}:</span>
          {item.rate ? (
            <span className="text-white font-mono">
              ${item.rate.sell?.toLocaleString("es-AR") ?? "—"}
            </span>
          ) : (
            <span className="text-gray-500">—</span>
          )}
        </div>
      ))}
    </div>
  );
}
