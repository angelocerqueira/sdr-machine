"use client";

import { scoreClass } from "./lead-app-mock";
import type { LeadAppDetail } from "./lead-app-types";

interface LaRailProps {
  lead: LeadAppDetail;
}

/* ─── Section 1: Score ─── */
function LaRailScore({ lead }: LaRailProps) {
  const cls = scoreClass(lead.opportunity_score);

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Score de oportunidade</span>
      </div>
      <div className="la-score-big">
        <div className={`la-score-num ${cls}`}>{lead.opportunity_score}</div>
        <div className="la-score-total">/100</div>
      </div>
      {lead.opportunity_score >= 60 && (
        <div className="la-score-caption">
          Acima do threshold (60)
        </div>
      )}
      <div className="la-score-dims">
        {(
          [
            ["acessibilidade", "Acessib."],
            ["lp", "Landing"],
            ["automacao", "Automação"],
            ["mapa", "Stack/SEO"],
          ] as const
        ).map(([k, label]) => {
          const v = lead.scores[k];
          const dcls = scoreClass(v);
          return (
            <div key={k} className="la-score-dim">
              <div className="la-score-dim-label">{label}</div>
              <div className="la-score-dim-bar">
                <span className={dcls} style={{ width: `${v}%` }} />
              </div>
              <div className="la-score-dim-val">{v}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Section 2: Recommendation ─── */
function LaRailReco({ lead }: LaRailProps) {
  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Recomendação</span>
      </div>
      <div className="la-reco">
        <div className="la-reco-head">Nível recomendado</div>
        <div className="la-reco-title">{lead.recommendation.label}</div>
      </div>
    </div>
  );
}

/* ─── Section 3: Details (KV grid) ─── */
function LaRailDetails({ lead }: LaRailProps) {
  const rows: [string, string][] = [
    ["Email", lead.email],
    ["Endereço", lead.endereco],
    ["CNPJ", lead.cnpj],
    ["Razão", lead.razao_social],
    ["Porte", lead.porte],
    ["CNAE", lead.cnae],
    ["Sócios", lead.socios.map((s) => s.nome).join(", ")],
  ];

  const hasData = rows.some(([, v]) => v);

  if (!hasData) return null;

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Cadastro</span>
      </div>
      <dl className="la-kv">
        {rows.map(([label, value]) =>
          value ? (
            <div key={label} className="la-kv-row">
              <dt>{label}</dt>
              <dd style={{ fontSize: 12 }}>{value}</dd>
            </div>
          ) : null
        )}
      </dl>
    </div>
  );
}

/* ─── Section 4: Enrichment sources ─── */
function LaRailSources({ lead }: LaRailProps) {
  if (lead.sources.length === 0) return null;

  const ok = lead.sources.filter((s) => s.status === "ok").length;

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Fontes de enriquecimento</span>
        <span
          style={{
            textTransform: "none",
            letterSpacing: 0,
            fontFamily: "var(--font-mono)",
            color: "var(--text-subtle)",
            fontSize: 10,
          }}
        >
          {ok}/{lead.sources.length}
        </span>
      </div>
      <div className="la-sources">
        {lead.sources.map((s, i) => (
          <div key={i} className="la-source">
            <span className={`la-source-dot ${s.status}`} />
            <div>
              <div className="la-source-name">{s.provider}</div>
              {s.note && (
                <div style={{ color: "var(--text-subtle)", fontSize: 10 }}>
                  {s.note}
                </div>
              )}
            </div>
            <div className="la-source-time">{s.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Main Rail ─── */
export function LaRail({ lead }: LaRailProps) {
  return (
    <aside className="la-rail">
      <LaRailScore lead={lead} />
      <LaRailReco lead={lead} />
      <LaRailDetails lead={lead} />
      <LaRailSources lead={lead} />
    </aside>
  );
}
