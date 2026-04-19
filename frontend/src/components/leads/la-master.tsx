"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { LEADS, groupLeads, scoreClass } from "./lead-app-mock";

const FILTERS = [
  { key: "all", label: "Todos" },
  { key: "my", label: "Meus" },
  { key: "hot", label: "Hot" },
  { key: "nicho", label: "Estética" },
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
}

export function LaMaster({ activeId, onSelect }: LaMasterProps) {
  const [filter, setFilter] = useState("all");
  const groups = groupLeads(LEADS);

  return (
    <aside className="la-master">
      <div className="la-master-head">
        <div className="la-master-title-row">
          <div className="la-master-title">Leads</div>
          <div className="la-master-count">{LEADS.length} / 87</div>
        </div>
        <div className="la-master-search">
          <span className="la-master-search-icon">
            <Icon name="search" size={14} />
          </span>
          <input placeholder="Buscar por nome, nicho, cidade\u2026" />
          <span className="la-master-search-kbd">\u2318K</span>
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
        {groups.map((g) => (
          <div key={g.key}>
            <div className="la-master-group">
              {g.title}
              <span className="count">\u00b7 {g.items.length}</span>
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
                    {l.niche} \u00b7 {l.city}
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
        ))}
      </div>
    </aside>
  );
}
