"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBarrios, type BarrioWithStats } from "@/lib/api";

type SortKey = "name" | "median_price_usd_m2" | "listing_count" | "avg_days_on_market" | "rental_yield_estimate";

export default function BarriosPage() {
  const [barrios, setBarrios] = useState<BarrioWithStats[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("median_price_usd_m2");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getBarrios()
      .then(setBarrios)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = barrios.filter((b) =>
    b.name.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortKey] ?? 0;
    const bVal = b[sortKey] ?? 0;
    if (typeof aVal === "string" && typeof bVal === "string") {
      return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortDir === "asc"
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-700 select-none"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortKey === field && (
          <svg className={`w-3 h-3 ${sortDir === "asc" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        )}
      </div>
    </th>
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-slate-200 rounded-lg animate-pulse" />
        <div className="h-[600px] bg-white rounded-2xl border border-slate-100 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Barrios de CABA</h1>
          <p className="text-sm text-slate-500 mt-0.5">{barrios.length} barrios</p>
        </div>
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            placeholder="Buscar barrio..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 w-56"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <SortHeader label="Barrio" field="name" />
                <th className="px-4 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Comuna
                </th>
                <SortHeader label="Mediana USD/m2" field="median_price_usd_m2" />
                <SortHeader label="Listings" field="listing_count" />
                <SortHeader label="Dias en Mercado" field="avg_days_on_market" />
                <SortHeader label="Rental Yield" field="rental_yield_estimate" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((barrio, idx) => (
                <tr key={barrio.id} className={`border-b border-slate-50 hover:bg-slate-50/50 transition-colors ${idx % 2 === 0 ? "" : "bg-slate-25"}`}>
                  <td className="px-4 py-3">
                    <Link
                      href={`/barrios/${barrio.slug}`}
                      className="text-indigo-600 hover:text-indigo-800 font-medium text-sm"
                    >
                      {barrio.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {barrio.comuna_name || `Comuna ${barrio.comuna_id}`}
                  </td>
                  <td className="px-4 py-3 text-sm font-mono font-semibold text-slate-800">
                    {barrio.median_price_usd_m2 !== null
                      ? `$${barrio.median_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                      : "\u2014"}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">
                    {barrio.listing_count?.toLocaleString() ?? "\u2014"}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">
                    {barrio.avg_days_on_market !== null
                      ? Math.round(barrio.avg_days_on_market)
                      : "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    {barrio.rental_yield_estimate !== null ? (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ${
                        barrio.rental_yield_estimate * 100 >= 5
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-600"
                      }`}>
                        {(barrio.rental_yield_estimate * 100).toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-sm text-slate-400">{"\u2014"}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
