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

  const sorted = [...barrios].sort((a, b) => {
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
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
      onClick={() => handleSort(field)}
    >
      {label} {sortKey === field ? (sortDir === "asc" ? "^" : "v") : ""}
    </th>
  );

  if (loading) {
    return <div className="animate-pulse text-gray-400">Cargando barrios...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Barrios de CABA</h1>
      <p className="text-sm text-gray-500">{barrios.length} barrios</p>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortHeader label="Barrio" field="name" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Comuna
                </th>
                <SortHeader label="Mediana USD/m2" field="median_price_usd_m2" />
                <SortHeader label="Listings" field="listing_count" />
                <SortHeader label="Dias en Mercado" field="avg_days_on_market" />
                <SortHeader label="Rental Yield" field="rental_yield_estimate" />
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sorted.map((barrio) => (
                <tr key={barrio.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/barrios/${barrio.slug}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {barrio.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {barrio.comuna_name || `Comuna ${barrio.comuna_id}`}
                  </td>
                  <td className="px-4 py-3 text-sm font-mono">
                    {barrio.median_price_usd_m2 !== null
                      ? `$${barrio.median_price_usd_m2.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {barrio.listing_count?.toLocaleString() ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {barrio.avg_days_on_market !== null
                      ? Math.round(barrio.avg_days_on_market)
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {barrio.rental_yield_estimate !== null
                      ? `${(barrio.rental_yield_estimate * 100).toFixed(1)}%`
                      : "—"}
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
