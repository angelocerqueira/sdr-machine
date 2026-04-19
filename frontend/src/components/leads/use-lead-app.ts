"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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

  // ---- Search + filter ----
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // ---- Leads list (from API) ----
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [leadsLoading, setLeadsLoading] = useState(true);

  const fetchLeads = useCallback((searchTerm: string, filter: string) => {
    const params: Record<string, string> = { per_page: "100", order_by: "score_desc" };
    if (searchTerm) params.search = searchTerm;
    if (filter === "hot") params.score_min = "80";
    else if (filter === "enriched") params.status = "enriched";
    else if (filter === "new") params.status = "scraped";

    setLeadsLoading(true);
    getLeads(params)
      .then((res) => setLeads(res.items.map(mapLeadToItem)))
      .catch(() => {})
      .finally(() => setLeadsLoading(false));
  }, []);

  // Initial fetch
  useEffect(() => { fetchLeads("", "all"); }, [fetchLeads]); // eslint-disable-line react-hooks/set-state-in-effect -- intentional: fetch on mount

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLeads(q, statusFilter), 300);
  }, [fetchLeads, statusFilter]);

  const handleFilter = useCallback((f: string) => {
    setStatusFilter(f);
    fetchLeads(search, f);
  }, [fetchLeads, search]);

  const refreshLeads = useCallback(() => {
    fetchLeads(search, statusFilter);
  }, [fetchLeads, search, statusFilter]);

  // ---- Lead detail (from API) ----
  const [lead, setLead] = useState<Lead | null>(null);
  const [leadLoading, setLeadLoading] = useState(false);
  const [leadError, setLeadError] = useState<string | null>(null);

  const fetchLead = useCallback((id: number) => {
    setLead(null);
    setLeadLoading(true);
    setLeadError(null);
    getLead(id)
      .then((data) => { setLead(data); setLeadLoading(false); })
      .catch((e) => { setLeadError(e.message); setLeadLoading(false); });
  }, []);

  useEffect(() => {
    if (!activeId || activeId <= 0) return;
    fetchLead(activeId); // eslint-disable-line react-hooks/set-state-in-effect -- intentional: fetch on activeId change
  }, [activeId, fetchLead]);

  const refreshLead = useCallback(() => {
    if (activeId && activeId > 0) fetchLead(activeId);
  }, [activeId, fetchLead]);

  // ---- Messages ----
  const [messages, setMessages] = useState<OutreachMessage[]>([]);

  const fetchMessages = useCallback((id: number) => {
    getLeadMessages(id).then(setMessages).catch(() => setMessages([]));
  }, []);

  useEffect(() => {
    if (!activeId || activeId <= 0) return;
    fetchMessages(activeId);
  }, [activeId, fetchMessages]);

  const refreshMessages = useCallback(() => {
    if (activeId && activeId > 0) fetchMessages(activeId);
  }, [activeId, fetchMessages]);

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
    leads,
    leadsLoading,
    lead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total: leads.length,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    refreshLead,
    refreshLeads,
    refreshMessages,
  };
}
