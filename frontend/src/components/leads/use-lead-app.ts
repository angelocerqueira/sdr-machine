"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getLeads, getLead, getLeadMessages } from "@/lib/api";
import type { Lead, OutreachMessage } from "@/lib/types";

export interface LeadListItem {
  id: number;
  name: string;
  niche: string;
  city: string;
  score: number;
  status: string;
}

function mapLeadToItem(l: Lead): LeadListItem {
  return {
    id: l.id,
    name: l.nome,
    niche: l.nicho || "",
    city: l.cidade || "",
    score: l.opportunity_score ?? 0,
    status: l.status,
  };
}

export function scoreClass(s: number): "high" | "mid" | "low" {
  if (s >= 80) return "high";
  if (s >= 50) return "mid";
  return "low";
}

const GROUP_DEFS = [
  { key: "hot", title: "Prontas pra call", statuses: ["responded"] },
  { key: "outreach", title: "Em outreach", statuses: ["outreach_sent", "outreach_ready"] },
  { key: "ready", title: "LP gerada", statuses: ["lp_generated"] },
  { key: "enriched", title: "Analisadas", statuses: ["enriched"] },
  { key: "new", title: "Novas", statuses: ["scraped"] },
  { key: "out", title: "Desqualificadas", statuses: ["disqualified"] },
];

export function groupLeads(list: LeadListItem[]) {
  return GROUP_DEFS.map((g) => ({
    ...g,
    items: list.filter((l) => g.statuses.includes(l.status)),
  })).filter((g) => g.items.length > 0);
}

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

  // ---- Leads list (from API) ----
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [leadsLoading, setLeadsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getLeads({ per_page: "200", order_by: "opportunity_score_desc" })
      .then((res) => { if (!cancelled) setLeads(res.items.map(mapLeadToItem)); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLeadsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  // ---- Lead detail (from API) ----
  const [lead, setLead] = useState<Lead | null>(null);
  const [leadLoading, setLeadLoading] = useState(false);
  const [leadError, setLeadError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeId || activeId <= 0) return;
    let cancelled = false;
    setLead(null); // eslint-disable-line react-hooks/set-state-in-effect -- intentional reset before fetch
    getLead(activeId)
      .then((data) => { if (!cancelled) { setLead(data); setLeadLoading(false); } })
      .catch((e) => { if (!cancelled) { setLeadError(e.message); setLeadLoading(false); } });
    return () => { cancelled = true; };
  }, [activeId]);

  // ---- Messages ----
  const [messages, setMessages] = useState<OutreachMessage[]>([]);

  useEffect(() => {
    if (!activeId || activeId <= 0) return;
    getLeadMessages(activeId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [activeId]);

  // ---- J/K keyboard navigation ----
  const currentIndex = activeId ? leads.findIndex((l) => l.id === activeId) : -1;

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
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
    theme,
    setTheme,
    leads,
    leadsLoading,
    lead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total: leads.length,
  };
}
