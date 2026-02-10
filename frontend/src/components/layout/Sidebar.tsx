"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/map", label: "Mapa", icon: "🗺️" },
  { href: "/barrios", label: "Barrios", icon: "🏘️" },
  { href: "/analytics/price-trends", label: "Tendencias", icon: "📈" },
  { href: "/analytics/rental-yield", label: "Rental Yield", icon: "💰" },
  { href: "/analytics/currency", label: "Moneda", icon: "💵" },
  { href: "/analytics/roi-simulator", label: "ROI Simulator", icon: "🧮" },
  { href: "/analytics/market-pulse", label: "Market Pulse", icon: "⚡" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <Link href="/dashboard" className="text-xl font-bold tracking-tight">
          POL Real Estate
        </Link>
        <p className="text-xs text-gray-400 mt-1">Buenos Aires Analytics</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        CABA Real Estate v0.1
      </div>
    </aside>
  );
}
