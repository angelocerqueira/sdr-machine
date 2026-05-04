"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { getLeads, getLead, getLeadMessages } from "@/lib/api";
import type { Lead, OutreachMessage, LeadProfile, NichoCanonico } from "@/lib/types";

export interface LeadListItem {
  id: number;
  name: string;
  niche: string;
  city: string;
  score: number;
  status: string;
  perfil_lead: LeadProfile | null;
}

function mapLeadToItem(l: Lead): LeadListItem {
  return {
    id: l.id,
    name: l.nome,
    niche: l.nicho || "",
    city: l.cidade || "",
    score: l.opportunity_score ?? 0,
    status: l.status,
    perfil_lead: l.perfil_lead ?? null,
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

const LS_KEYS = {
  tab: "sdr-lead-tab",
  search: "sdr-leads-search",
  status: "sdr-leads-status-filter",
  perfil: "sdr-leads-perfil-filter",
  nichoCanon: "sdr-leads-nicho-canon-filter",
  activeId: "sdr-leads-active-id",
} as const;

function readLS(key: string, fallback = ""): string {
  if (typeof window === "undefined") return fallback;
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}

function writeLS(key: string, value: string) {
  if (typeof window === "undefined") return;
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {}
}

export function useLeadApp(activeId: number | null) {
  const router = useRouter();

  // Tab state (persisted)
  const [activeTab, setActiveTabState] = useState(() => readLS(LS_KEYS.tab, "diag") || "diag");
  const setActiveTab = useCallback((tab: string) => {
    setActiveTabState(tab);
    writeLS(LS_KEYS.tab, tab);
  }, []);

  // ---- Search + filter (persisted) ----
  const [search, setSearch] = useState(() => readLS(LS_KEYS.search));
  const [statusFilter, setStatusFilter] = useState(() => readLS(LS_KEYS.status, "all") || "all");
  const [perfilFilter, setPerfilFilter] = useState<LeadProfile | "">(() => readLS(LS_KEYS.perfil) as LeadProfile | "");
  const [nichoCanonFilter, setNichoCanonFilter] = useState<NichoCanonico | "">(() => readLS(LS_KEYS.nichoCanon) as NichoCanonico | "");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Persist active lead id when it changes
  useEffect(() => {
    if (activeId && activeId > 0) writeLS(LS_KEYS.activeId, String(activeId));
  }, [activeId]);

  // ---- Leads list (from API) ----
  const PER_PAGE = 30;
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [leadsLoading, setLeadsLoading] = useState(true);

  const fetchLeads = useCallback((
    searchTerm: string,
    filter: string,
    pageNum: number,
    append: boolean,
    perfil: LeadProfile | "" = "",
    nichoCanon: NichoCanonico | "" = "",
  ) => {
    const params: Record<string, string> = {
      per_page: String(PER_PAGE),
      page: String(pageNum),
      order_by: "score_desc",
    };
    if (searchTerm) params.search = searchTerm;
    if (filter === "hot") params.score_min = "80";
    else if (filter === "enriched") params.status = "enriched";
    else if (filter === "new") params.status = "scraped";
    if (perfil) params.perfil_lead = perfil;
    if (nichoCanon) params.nicho_canonico = nichoCanon;

    if (append) setLoadingMore(true);
    else setLeadsLoading(true);

    getLeads(params)
      .then((res) => {
        const items = res.items.map(mapLeadToItem);
        setLeads((prev) => (append ? [...prev, ...items] : items));
        setTotal(res.total);
        setPage(pageNum);
      })
      .catch(() => { if (!append) { setLeads([]); setTotal(0); } })
      .finally(() => {
        if (append) setLoadingMore(false);
        else setLeadsLoading(false);
      });
  }, []);

  // Initial fetch (uses restored filters)
  useEffect(() => { fetchLeads(search, statusFilter, 1, false, perfilFilter, nichoCanonFilter); }, [fetchLeads]); // eslint-disable-line react-hooks/exhaustive-deps,react-hooks/set-state-in-effect -- intentional: fetch once on mount with restored filters

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    writeLS(LS_KEYS.search, q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLeads(q, statusFilter, 1, false, perfilFilter, nichoCanonFilter), 300);
  }, [fetchLeads, statusFilter, perfilFilter, nichoCanonFilter]);

  const handleFilter = useCallback((f: string) => {
    setStatusFilter(f);
    writeLS(LS_KEYS.status, f);
    fetchLeads(search, f, 1, false, perfilFilter, nichoCanonFilter);
  }, [fetchLeads, search, perfilFilter, nichoCanonFilter]);

  const handlePerfilFilter = useCallback((p: LeadProfile | "") => {
    setPerfilFilter(p);
    writeLS(LS_KEYS.perfil, p);
    fetchLeads(search, statusFilter, 1, false, p, nichoCanonFilter);
  }, [fetchLeads, search, statusFilter, nichoCanonFilter]);

  const handleNichoCanonFilter = useCallback((n: NichoCanonico | "") => {
    setNichoCanonFilter(n);
    writeLS(LS_KEYS.nichoCanon, n);
    fetchLeads(search, statusFilter, 1, false, perfilFilter, n);
  }, [fetchLeads, search, statusFilter, perfilFilter]);

  const refreshLeads = useCallback(() => {
    fetchLeads(search, statusFilter, 1, false, perfilFilter, nichoCanonFilter);
  }, [fetchLeads, search, statusFilter, perfilFilter, nichoCanonFilter]);

  const loadMore = useCallback(() => {
    fetchLeads(search, statusFilter, page + 1, true, perfilFilter, nichoCanonFilter);
  }, [fetchLeads, search, statusFilter, page, perfilFilter, nichoCanonFilter]);

  // ---- Lead detail (from API) ----
  const [lead, setLead] = useState<Lead | null>(null);
  const [leadLoading, setLeadLoading] = useState(false);
  const [leadError, setLeadError] = useState<string | null>(null);
  const latestLeadReqRef = useRef<number>(0);

  const fetchLead = useCallback((id: number) => {
    // Stale-while-revalidate: keep previous lead visible during fetch.
    // Track latest request to ignore out-of-order responses on fast J/K nav.
    latestLeadReqRef.current = id;
    setLeadLoading(true);
    setLeadError(null);
    getLead(id)
      .then((data) => {
        if (latestLeadReqRef.current !== id) return;
        setLead(data);
        setLeadLoading(false);
      })
      .catch((e) => {
        if (latestLeadReqRef.current !== id) return;
        setLeadError(e.message);
        setLeadLoading(false);
      });
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
  const latestMsgReqRef = useRef<number>(0);

  const fetchMessages = useCallback((id: number) => {
    latestMsgReqRef.current = id;
    getLeadMessages(id)
      .then((data) => { if (latestMsgReqRef.current === id) setMessages(data); })
      .catch(() => { if (latestMsgReqRef.current === id) setMessages([]); });
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
    loadingMore,
    lead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total,
    hasMore: leads.length < total,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    perfilFilter,
    handlePerfilFilter,
    nichoCanonFilter,
    handleNichoCanonFilter,
    loadMore,
    refreshLead,
    refreshLeads,
    refreshMessages,
  };
}
