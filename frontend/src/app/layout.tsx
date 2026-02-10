import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import CurrencyTicker from "@/components/ui/CurrencyTicker";
import MobileSidebarProvider from "@/components/layout/MobileSidebarProvider";
import HamburgerButton from "@/components/layout/HamburgerButton";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "POL Real Estate - Buenos Aires Analytics",
  description: "Plataforma de analytics inmobiliario para Buenos Aires (CABA)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#f8fafc]`}
      >
        <MobileSidebarProvider>
          <div className="flex min-h-[100dvh]">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0">
              <header className="h-14 bg-white/80 backdrop-blur-md border-b border-slate-200/60 flex items-center px-4 md:px-6 justify-between sticky top-0 z-30">
                <div className="flex items-center gap-2">
                  <HamburgerButton />
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-medium text-slate-400 tracking-wide uppercase">Live</span>
                </div>
                <CurrencyTicker />
              </header>
              <main className="flex-1 p-4 md:p-6 overflow-auto">{children}</main>
            </div>
          </div>
        </MobileSidebarProvider>
      </body>
    </html>
  );
}
