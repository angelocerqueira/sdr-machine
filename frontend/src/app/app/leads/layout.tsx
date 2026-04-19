"use client";

import { useState, useEffect, createContext, useContext } from "react";
import "@/components/leads/lead-app.css";

interface RailContextValue {
  railOpen: boolean;
  setRailOpen: (open: boolean) => void;
}

const RailContext = createContext<RailContextValue>({ railOpen: true, setRailOpen: () => {} });

export function useRailContext() {
  return useContext(RailContext);
}

export default function LeadAppLayout({ children }: { children: React.ReactNode }) {
  const [railOpen, setRailOpen] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("sdr-rail-open");
        if (saved !== null) return saved === "true";
      } catch {}
    }
    return true;
  });

  useEffect(() => {
    try { localStorage.setItem("sdr-rail-open", String(railOpen)); } catch {}
  }, [railOpen]);

  // Collapse rail on narrow viewports
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1199px)");
    function handleChange(e: MediaQueryListEvent | MediaQueryList) {
      if (e.matches) setRailOpen(false);
    }
    handleChange(mq);
    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

  const shellClass = `la-shell${railOpen ? " rail-open" : ""}`;

  return (
    <RailContext.Provider value={{ railOpen, setRailOpen }}>
      <div className={shellClass}>
        {children}
      </div>
    </RailContext.Provider>
  );
}
