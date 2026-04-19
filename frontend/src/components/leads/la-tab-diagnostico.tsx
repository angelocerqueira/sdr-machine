"use client";

import { Icon } from "@/components/ui";
import { scoreClass } from "./lead-app-mock";
import type { LeadAppDetail } from "./lead-app-types";

const DIMS: [string, string][] = [
  ["acessibilidade", "Acessibilidade"],
  ["lp", "Landing"],
  ["automacao", "Automação"],
  ["mapa", "Stack / SEO"],
];

export function LaTabDiag({ lead }: { lead: LeadAppDetail }) {
  const byId = new Map(lead.checklist.map((c) => [c.id, c]));

  return (
    <div>
      {/* Summary strip */}
      <div className="la-diag-summary">
        {DIMS.map(([k, label]) => {
          const v = lead.scores[k as keyof typeof lead.scores];
          const cls = scoreClass(v);
          return (
            <div key={k} className="la-diag-dim">
              <div className="la-diag-dim-label">{label}</div>
              <div className={`la-diag-dim-value ${cls}`}>{v}</div>
              <div className="la-diag-dim-bar">
                <span className={cls} style={{ width: `${v}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Checklist groups */}
      {lead.checklist_groups.map((g) => (
        <div key={g.key} className="la-checklist-group">
          <div className="la-checklist-group-head">
            <div className="la-checklist-group-title">{g.title}</div>
            <div className="la-checklist-group-count">
              {g.ids.length} {g.ids.length === 1 ? "gap" : "gaps"}
            </div>
            <div className="la-checklist-group-hint">{g.hint}</div>
          </div>
          {g.ids.map((id) => {
            const c = byId.get(id);
            if (!c) return null;
            return (
              <div key={id} className="la-check">
                <div className={`la-check-mark ${c.weight}`}>
                  <Icon name={c.weight === "high" ? "warn" : "info"} size={12} />
                </div>
                <div className="la-check-body">
                  <div className="la-check-head">
                    <span className="la-check-dim">{c.dim_label}</span>
                    <span className="la-check-title">{c.title}</span>
                  </div>
                  <div className="la-check-ev">{c.evidence}</div>
                </div>
                <div className="la-check-impact">
                  <strong>{c.impact}</strong>
                  {c.impact_detail}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
