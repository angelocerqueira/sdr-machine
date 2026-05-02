"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { Icon } from "@/components/ui";
import { getLeads } from "@/lib/api";
import type { Lead } from "@/lib/types";

const PER_PAGE = 20;

type ColumnTone = "muted" | "accent" | "warn" | "ok";

const TONE_BY_STATUS: Record<string, ColumnTone> = {
  scraped: "muted",
  enriched: "accent",
  lp_generated: "accent",
  outreach_ready: "warn",
  outreach_sent: "warn",
  responded: "ok",
  in_call: "ok",
  closed: "ok",
  delivered: "ok",
  disqualified: "muted",
  failed: "muted",
};

const EMPTY_HINTS: Record<string, string> = {
  scraped: "rode o scrape pra popular",
  enriched: "rode enriquecer pra popular",
  lp_generated: "leads analisados aparecem aqui",
  outreach_ready: "depois da geração de LP",
  outreach_sent: "depois de disparar mensagens",
  responded: "respostas chegam aqui",
  in_call: "leads em call",
  closed: "fechados aparecem aqui",
  delivered: "entregues aparecem aqui",
  disqualified: "desqualificados aparecem aqui",
  failed: "falhas aparecem aqui",
};

interface KanbanColumnProps {
  id: string;
  label: string;
  count: number;
  refreshKey: number;
  filterNicho?: string;
  filterCidade?: string;
  filterScoreMin?: string;
  filterPerfil?: string;
  filterNichoCanon?: string;
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
  filterPerfil,
  filterNichoCanon,
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

  const tone: ColumnTone = TONE_BY_STATUS[id] ?? "muted";
  const isFailureColumn = id === "disqualified" || id === "failed";

  const hasMore = leads.length < total;

  const buildParams = useCallback(() => {
    const params: Record<string, string> = {
      status: id,
      per_page: String(PER_PAGE),
    };
    if (filterNicho) params.nicho = filterNicho;
    if (filterCidade) params.cidade = filterCidade;
    if (filterScoreMin) params.score_min = filterScoreMin;
    if (filterPerfil) params.perfil_lead = filterPerfil;
    if (filterNichoCanon) params.nicho_canonico = filterNichoCanon;
    if (search) params.search = search;
    params.order_by = orderBy || "score_desc";
    return params;
  }, [id, filterNicho, filterCidade, filterScoreMin, filterPerfil, filterNichoCanon, search, orderBy]);

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

  useEffect(() => {
    setTotal(count);
  }, [count]);

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
      className={`pl-kbn-col${isOver ? " active" : ""}`}
      style={{ minWidth: 280, width: 280 }}
    >
      <header className="pl-kbn-col-head">
        <div className="pl-kbn-col-title-wrap">
          <span className={`pl-kbn-col-pip pl-kbn-col-pip-${tone}`} />
          <span className="pl-kbn-col-title">{label}</span>
        </div>
        <div className="pl-kbn-col-meta">
          <span
            className="pl-kbn-col-count"
            style={
              isFailureColumn && total > 0
                ? { color: "var(--danger)", background: "var(--danger-soft)" }
                : undefined
            }
          >
            {total}
          </span>
        </div>
      </header>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="pl-kbn-col-body"
      >
        {loading ? (
          <>
            {[0, 1, 2].map((i) => (
              <div key={i} className="pl-card" style={{ minHeight: 84 }}>
                <div className="pl-card-rail" />
                <div className="pl-card-body">
                  <div className="skeleton" style={{ height: 12, width: "70%" }} />
                  <div className="skeleton" style={{ height: 10, width: "50%", marginTop: 6 }} />
                </div>
              </div>
            ))}
          </>
        ) : leads.length === 0 ? (
          <div className="pl-kbn-empty">
            <div className="pl-kbn-empty-icon">
              <Icon name="empty" size={18} />
            </div>
            <div className="pl-kbn-empty-msg">Nenhum lead</div>
            <div className="pl-kbn-empty-hint">{EMPTY_HINTS[id] ?? ""}</div>
          </div>
        ) : (
          <>
            {leads.map((lead) => (
              <KanbanCard key={lead.id} lead={lead} onSelect={onSelectLead} />
            ))}
            {loadingMore && (
              <div style={{ display: "flex", justifyContent: "center", padding: "8px 0" }}>
                <span
                  style={{
                    width: 12,
                    height: 12,
                    border: "2px solid var(--text-muted)",
                    borderTopColor: "var(--accent)",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                  }}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
