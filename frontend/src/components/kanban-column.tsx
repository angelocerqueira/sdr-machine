"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { KanbanCard } from "./kanban-card";
import { getLeads } from "@/lib/api";
import type { Lead } from "@/lib/types";

const PER_PAGE = 20;

interface KanbanColumnProps {
  id: string;
  label: string;
  count: number;
  refreshKey: number;
  filterNicho?: string;
  filterCidade?: string;
  filterScoreMin?: string;
  search?: string;
  orderBy?: string;
  onSelectLead: (id: number) => void;
}

export function KanbanColumn({
  id,
  label,
  count,
  refreshKey,
  filterNicho,
  filterCidade,
  filterScoreMin,
  search,
  orderBy,
  onSelectLead,
}: KanbanColumnProps) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(count);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { setNodeRef, isOver } = useDroppable({ id });

  const hasMore = leads.length < total;

  const buildParams = useCallback(() => {
    const params: Record<string, string> = {
      status: id,
      per_page: String(PER_PAGE),
    };
    if (filterNicho) params.nicho = filterNicho;
    if (filterCidade) params.cidade = filterCidade;
    if (filterScoreMin) params.score_min = filterScoreMin;
    if (search) params.search = search;
    params.order_by = orderBy || "score_desc";
    return params;
  }, [id, filterNicho, filterCidade, filterScoreMin, search, orderBy]);

  // Load first page (also re-runs on filter change or refreshKey bump)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setPage(1);

    const params = { ...buildParams(), page: "1" };
    getLeads(params)
      .then((data) => {
        if (!cancelled) {
          setLeads(data.items);
          setTotal(data.total);
        }
      })
      .catch((err) => console.error(`Erro ao carregar leads (${id}):`, err))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [buildParams, refreshKey, id]);

  // Sync count from parent
  useEffect(() => {
    setTotal(count);
  }, [count]);

  // Load more (infinite scroll)
  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;
    const nextPage = page + 1;
    setLoadingMore(true);

    const params = { ...buildParams(), page: String(nextPage) };
    getLeads(params)
      .then((data) => {
        setLeads((prev) => [...prev, ...data.items]);
        setTotal(data.total);
        setPage(nextPage);
      })
      .catch((err) => console.error(`Erro ao carregar mais leads (${id}):`, err))
      .finally(() => setLoadingMore(false));
  }, [page, loadingMore, hasMore, buildParams, id]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (nearBottom) loadMore();
  }, [loadMore]);

  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border bg-surface min-w-[240px] w-[240px] flex flex-col transition-default ${
        isOver ? "border-accent/40 bg-accent-subtle" : "border-border"
      }`}
    >
      {/* Column header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
        <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)]">
          {label}
        </h3>
        <span
          className={`text-[11px] font-medium font-[family-name:var(--font-mono)] rounded-full px-2 py-0.5 ${
            total > 0
              ? "bg-accent-subtle text-accent"
              : "bg-surface-raised text-text-muted"
          }`}
        >
          {total}
        </span>
      </div>

      {/* Cards with scroll */}
      <SortableContext
        items={leads.map((l) => l.id)}
        strategy={verticalListSortingStrategy}
      >
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex flex-col gap-2 p-2 flex-1 min-h-[120px] max-h-[calc(100vh-320px)] overflow-y-auto"
        >
          {loading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="rounded-lg border border-border-subtle p-3 space-y-2">
                  <div className="skeleton h-3.5 w-3/4" />
                  <div className="flex justify-between">
                    <div className="skeleton h-3 w-16" />
                    <div className="skeleton h-3 w-8" />
                  </div>
                </div>
              ))}
            </div>
          ) : leads.length === 0 ? (
            <p className="text-[11px] text-text-muted text-center py-8 font-[family-name:var(--font-mono)]">
              Nenhum lead
            </p>
          ) : (
            <>
              {leads.map((lead) => (
                <KanbanCard key={lead.id} lead={lead} onSelect={onSelectLead} />
              ))}
              {loadingMore && (
                <div className="flex items-center justify-center py-2">
                  <span className="w-3 h-3 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
                </div>
              )}
            </>
          )}
        </div>
      </SortableContext>
    </div>
  );
}
