"use client";

import { useEffect, useState } from "react";

const DOLAR_API_URL = "https://dolarapi.com/v1/dolares";

interface DolarAPIRate {
  casa: string;
  compra: number;
  venta: number;
  fechaActualizacion: string;
}

interface TickerRate {
  buy: number | null;
  sell: number | null;
}

const CASA_MAP: Record<string, string> = {
  blue: "blue",
  oficial: "oficial",
  bolsa: "mep",
  contadoconliqui: "ccl",
};

export default function CurrencyTicker() {
  const [rates, setRates] = useState<Record<string, TickerRate> | null>(null);

  useEffect(() => {
    const fetchRates = async () => {
      try {
        const res = await fetch(DOLAR_API_URL);
        if (!res.ok) return;
        const data: DolarAPIRate[] = await res.json();

        const mapped: Record<string, TickerRate> = {};
        for (const item of data) {
          const key = CASA_MAP[item.casa?.toLowerCase()];
          if (key) {
            mapped[key] = { buy: item.compra, sell: item.venta };
          }
        }
        setRates(mapped);
      } catch {
        // ticker is non-critical
      }
    };
    fetchRates();
    const interval = setInterval(fetchRates, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (!rates) {
    return (
      <div className="flex items-center gap-1.5 md:gap-3">
        {[1, 2].map((i) => (
          <div key={i} className="h-7 w-24 bg-slate-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  const items = [
    { label: "Blue", key: "blue", color: "text-indigo-600 bg-indigo-50 border-indigo-100" },
    { label: "Oficial", key: "oficial", color: "text-slate-600 bg-slate-50 border-slate-100" },
    { label: "MEP", key: "mep", color: "text-emerald-600 bg-emerald-50 border-emerald-100" },
    { label: "CCL", key: "ccl", color: "text-amber-600 bg-amber-50 border-amber-100" },
  ];

  return (
    <div className="flex items-center gap-1.5 md:gap-2">
      {items.map((item) => {
        const rate = rates[item.key];
        const hiddenOnMobile = item.key === "oficial" || item.key === "ccl";
        return (
          <div
            key={item.label}
            className={`${hiddenOnMobile ? "hidden sm:flex" : "flex"} items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${item.color}`}
          >
            <span className="opacity-70">{item.label}</span>
            {rate ? (
              <span className="font-mono font-semibold">
                ${rate.sell?.toLocaleString("es-AR") ?? "\u2014"}
              </span>
            ) : (
              <span className="opacity-40">{"\u2014"}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
