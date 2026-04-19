"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { LEADS } from "./lead-app-mock";

export function useLeadApp(activeId: number | null) {
  const router = useRouter();

  // Tab state (persisted)
  const [activeTab, setActiveTabState] = useState(() => {
    if (typeof window !== "undefined") {
      try { return localStorage.getItem("sdr-lead-tab") || "diag"; } catch {}
    }
    return "diag";
  });
  const setActiveTab = useCallback((tab: string) => {
    setActiveTabState(tab);
    try { localStorage.setItem("sdr-lead-tab", tab); } catch {}
  }, []);

  // Filter state
  const [filter, setFilter] = useState("all");

  // Theme state
  const [theme, setThemeState] = useState(() => {
    if (typeof document !== "undefined") {
      return document.documentElement.getAttribute("data-theme") || "light";
    }
    return "light";
  });

  const setTheme = useCallback((t: string) => {
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("sdr-theme", t); } catch {}
  }, []);

  // J/K keyboard navigation
  const leads = LEADS; // TODO: replace with API data
  const currentIndex = activeId ? leads.findIndex((l) => l.id === activeId) : -1;

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't capture when typing in inputs
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement).isContentEditable) return;

      if (e.key === "j" && currentIndex < leads.length - 1) {
        e.preventDefault();
        router.push(`/app/leads/${leads[currentIndex + 1].id}`);
      }
      if (e.key === "k" && currentIndex > 0) {
        e.preventDefault();
        router.push(`/app/leads/${leads[currentIndex - 1].id}`);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, leads, router]);

  return {
    activeTab,
    setActiveTab,
    filter,
    setFilter,
    theme,
    setTheme,
    leads,
    currentIndex,
    total: leads.length,
  };
}
