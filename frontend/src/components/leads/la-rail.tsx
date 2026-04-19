"use client";

import { Icon } from "@/components/ui";
import { scoreClass } from "./lead-app-mock";
import type { LeadAppDetail } from "./lead-app-types";

interface LaRailProps {
  lead: LeadAppDetail;
}

/* ─── Section 1: Score ─── */
function LaRailScore({ lead }: LaRailProps) {
  const cls = scoreClass(lead.opportunity_score);
  const delta =
    lead.opportunity_score - (lead.score_previous ?? lead.opportunity_score);

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Score de oportunidade</span>
        <span
          style={{
            textTransform: "none",
            letterSpacing: 0,
            fontFamily: "var(--font-mono)",
            color: "var(--text-subtle)",
            fontSize: 10,
          }}
        >
          v2 · re-enrich 18/04
        </span>
      </div>
      <div className="la-score-big">
        <div className={`la-score-num ${cls}`}>{lead.opportunity_score}</div>
        <div className="la-score-total">/100</div>
        {delta > 0 && (
          <div className="la-score-trend">
            <Icon
              name="arrow-r"
              size={12}
              style={{ transform: "rotate(-45deg)" }}
            />{" "}
            +{delta}
          </div>
        )}
      </div>
      <div className="la-score-caption">
        Acima do threshold (60) · fila qualificada
      </div>
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
        <div className="la-reco-body">{lead.recommendation.summary}</div>
        <div className="la-reco-price">
          <span>Ticket sugerido</span>
          <strong>
            R${" "}
            {lead.recommendation.price_low.toLocaleString("pt-BR")}\u2013
            {lead.recommendation.price_high.toLocaleString("pt-BR")}
          </strong>
        </div>
        <div
          className="la-reco-price"
          style={{ borderTop: 0, paddingTop: 0 }}
        >
          <span>Entrega</span>
          <strong>{lead.recommendation.delivery_weeks} semana</strong>
        </div>
      </div>
    </div>
  );
}

/* ─── Section 3: Details (KV grid) ─── */
function LaRailDetails({ lead }: LaRailProps) {
  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Cadastro</span>
        <button className="la-rail-head-action">Editar</button>
      </div>
      <dl className="la-kv">
        <div className="la-kv-row">
          <dt>Email</dt>
          <dd className="mono" style={{ fontSize: 11 }}>
            {lead.email}
          </dd>
        </div>
        <div className="la-kv-row">
          <dt>Endereço</dt>
          <dd style={{ fontSize: 12 }}>{lead.endereco}</dd>
        </div>
        <div className="la-kv-row">
          <dt>CNPJ</dt>
          <dd className="mono">{lead.cnpj}</dd>
        </div>
        <div className="la-kv-row">
          <dt>Razão</dt>
          <dd style={{ fontSize: 12 }}>{lead.razao_social}</dd>
        </div>
        <div className="la-kv-row">
          <dt>Porte</dt>
          <dd>{lead.porte}</dd>
        </div>
        <div className="la-kv-row">
          <dt>CNAE</dt>
          <dd className="mono" style={{ fontSize: 11 }}>
            {lead.cnae}
          </dd>
        </div>
        <div className="la-kv-row">
          <dt>Sócios</dt>
          <dd style={{ fontSize: 12 }}>
            {lead.socios.map((s) => s.nome).join(", ")}
          </dd>
        </div>
      </dl>
    </div>
  );
}

/* ─── Section 4: Enrichment sources ─── */
function LaRailSources({ lead }: LaRailProps) {
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
              <div
                style={{
                  color: "var(--text-subtle)",
                  fontSize: 10,
                }}
              >
                {s.note}
              </div>
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
