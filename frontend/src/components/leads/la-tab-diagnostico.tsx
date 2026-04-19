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
  const hasScores = Object.values(lead.scores).some((v) => v > 0);
  const reasons = lead.opportunity_reasons;

  if (!hasScores && reasons.length === 0) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="search" size={20} />
        </div>
        <div className="state-title">Sem diagnóstico</div>
        <div className="state-msg">
          Este lead ainda não foi enriquecido. Execute o enriquecimento para gerar o diagnóstico.
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Summary strip */}
      {hasScores && (
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
      )}

      {/* Opportunity reasons */}
      {reasons.length > 0 && (
        <div className="la-checklist-group">
          <div className="la-checklist-group-head">
            <div className="la-checklist-group-title">Sinais de oportunidade</div>
            <div className="la-checklist-group-count">
              {reasons.length} {reasons.length === 1 ? "sinal" : "sinais"}
            </div>
          </div>
          {reasons.map((reason, i) => {
            const tag = reason.match(/^\[([A-Z_]+)\]/)?.[1] || "";
            const text = reason.replace(/^\[[A-Z_]+\]\s*/, "");
            return (
              <div key={i} className="la-check">
                <div className={`la-check-mark ${tag.includes("CRITICAL") ? "high" : "mid"}`}>
                  <Icon name={tag.includes("CRITICAL") ? "warn" : "info"} size={12} />
                </div>
                <div className="la-check-body">
                  <div className="la-check-head">
                    {tag && <span className="la-check-dim">{tag.replace(/_/g, " ").toLowerCase()}</span>}
                    <span className="la-check-title">{text}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
