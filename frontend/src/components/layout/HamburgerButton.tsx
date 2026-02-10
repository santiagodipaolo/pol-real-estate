"use client";

import { useMobileSidebar } from "./MobileSidebarProvider";

export default function HamburgerButton() {
  const { toggle } = useMobileSidebar();

  return (
    <button
      onClick={toggle}
      className="md:hidden flex items-center justify-center w-11 h-11 -ml-2 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
      aria-label="Toggle menu"
    >
      <svg
        className="w-5 h-5"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
        />
      </svg>
    </button>
  );
}
