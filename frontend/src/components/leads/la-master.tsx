"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { scoreClass, groupLeads, type LeadListItem } from "./use-lead-app";

const FILTERS = [
  { key: "all", label: "Todos" },
  { key: "hot", label: "Hot" },
  { key: "enriched", label: "Analisadas" },
  { key: "new", label: "Novas" },
];

const STATUS_DOT_LABEL: Record<string, string> = {
  scraped: "Novo",
  enriched: "Analisado",
  lp_generated: "LP pronta",
  outreach_ready: "Msg pronta",
  outreach_sent: "Enviado",
  responded: "Respondeu",
  closed: "Fechado",
  disqualified: "Desqual.",
};

interface LaMasterProps {
  activeId: number;
  onSelect: (id: number) => void;
  leads: LeadListItem[];
  loading?: boolean;
}

export function LaMaster({ activeId, onSelect, leads, loading }: LaMasterProps) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = leads.filter((l) => {
    if (search) {
      const q = search.toLowerCase();
      if (!l.name.toLowerCase().includes(q) && !l.niche.toLowerCase().includes(q) && !l.city.toLowerCase().includes(q)) return false;
    }
    if (filter === "hot") return l.score >= 80;
    if (filter === "enriched") return l.status === "enriched";
    if (filter === "new") return l.status === "scraped";
    return true;
  });

  const groups = groupLeads(filtered);

  return (
    <aside className="la-master">
      <div className="la-master-head">
        <div className="la-master-title-row">
          <div className="la-master-title">Leads</div>
          <div className="la-master-count">{filtered.length} / {leads.length}</div>
        </div>
        <div className="la-master-search">
          <span className="la-master-search-icon">
            <Icon name="search" size={14} />
          </span>
          <input
            placeholder="Buscar por nome, nicho, cidade…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span className="la-master-search-kbd">⌘K</span>
        </div>
      </div>
      <div className="la-master-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`la-master-filter ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>
      <div className="la-master-body">
        {loading ? (
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 52, borderRadius: "var(--r-2)" }} />
            ))}
          </div>
        ) : groups.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
            Nenhum lead encontrado
          </div>
        ) : (
          groups.map((g) => (
            <div key={g.key}>
              <div className="la-master-group">
                {g.title}
                <span className="count">· {g.items.length}</span>
              </div>
              {g.items.map((l) => (
                <button
                  key={l.id}
                  className={`la-master-item ${l.id === activeId ? "active" : ""}`}
                  onClick={() => onSelect(l.id)}
                >
                  <div className={`la-master-score ${scoreClass(l.score)}`}>
                    {l.score}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div className="la-master-name">{l.name}</div>
                    <div className="la-master-meta">
                      {l.niche} · {l.city}
                    </div>
                  </div>
                  <div
                    className="la-master-status"
                    title={STATUS_DOT_LABEL[l.status]}
                  >
                    <span className={`la-master-status-dot ${l.status}`} />
                  </div>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
