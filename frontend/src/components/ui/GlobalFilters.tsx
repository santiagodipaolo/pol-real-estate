"use client";

import { useState } from "react";

interface GlobalFiltersProps {
  onFilterChange: (filters: FilterState) => void;
  showPriceRange?: boolean;
}

export interface FilterState {
  operationType: string;
  propertyType: string;
  priceMin?: number;
  priceMax?: number;
  currency: string;
}

const operationTypes = [
  { value: "", label: "Todas" },
  { value: "sale", label: "Venta" },
  { value: "rent", label: "Alquiler" },
];

const propertyTypes = [
  { value: "", label: "Todos" },
  { value: "apartment", label: "Departamento" },
  { value: "house", label: "Casa" },
  { value: "ph", label: "PH" },
  { value: "land", label: "Terreno" },
  { value: "office", label: "Oficina" },
];

const currencies = [
  { value: "usd_blue", label: "USD Blue" },
  { value: "usd_official", label: "USD Oficial" },
  { value: "usd_mep", label: "USD MEP" },
];

const selectClass =
  "px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400";

export default function GlobalFilters({
  onFilterChange,
  showPriceRange = false,
}: GlobalFiltersProps) {
  const [filters, setFilters] = useState<FilterState>({
    operationType: "sale",
    propertyType: "",
    currency: "usd_blue",
  });

  const update = (key: keyof FilterState, value: string | number) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onFilterChange(next);
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={filters.operationType}
        onChange={(e) => update("operationType", e.target.value)}
        className={selectClass}
      >
        {operationTypes.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      <select
        value={filters.propertyType}
        onChange={(e) => update("propertyType", e.target.value)}
        className={selectClass}
      >
        {propertyTypes.map((p) => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
      </select>

      <select
        value={filters.currency}
        onChange={(e) => update("currency", e.target.value)}
        className={selectClass}
      >
        {currencies.map((c) => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </select>

      {showPriceRange && (
        <>
          <input
            type="number"
            placeholder="Precio min"
            onChange={(e) => update("priceMin", Number(e.target.value))}
            className={`w-28 ${selectClass}`}
          />
          <input
            type="number"
            placeholder="Precio max"
            onChange={(e) => update("priceMax", Number(e.target.value))}
            className={`w-28 ${selectClass}`}
          />
        </>
      )}
    </div>
  );
}
