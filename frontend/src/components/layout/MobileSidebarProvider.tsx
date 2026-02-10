"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";

interface MobileSidebarContextType {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

const MobileSidebarContext = createContext<MobileSidebarContextType>({
  isOpen: false,
  open: () => {},
  close: () => {},
  toggle: () => {},
});

export function useMobileSidebar() {
  return useContext(MobileSidebarContext);
}

export default function MobileSidebarProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  useEffect(() => {
    if (isOpen) {
      document.body.classList.add("sidebar-open");
    } else {
      document.body.classList.remove("sidebar-open");
    }
    return () => document.body.classList.remove("sidebar-open");
  }, [isOpen]);

  return (
    <MobileSidebarContext.Provider value={{ isOpen, open, close, toggle }}>
      {children}
    </MobileSidebarContext.Provider>
  );
}
