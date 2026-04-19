"use client";

import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "./lead-app-types";

export function LaTabLp({ lead }: { lead: LeadAppDetail }) {
  const m = lead.lp_metrics;

  return (
    <div className="la-lp">
      {/* Left: Preview */}
      <div className="la-lp-preview">
        <div className="la-lp-chrome">
          <div className="la-lp-lights">
            <span />
            <span />
            <span />
          </div>
          <div className="la-lp-url">sdr.machine/lp/{lead.public_id}</div>
          <button className="la-msg-icon-btn" title="Copiar">
            <Icon name="copy" size={14} />
          </button>
          <button className="la-msg-icon-btn" title="Abrir">
            <Icon name="external" size={14} />
          </button>
        </div>
        <div className="la-lp-frame">
          <div className="la-lp-page">
            <div className="eyebrow">Clínica BelaForma · Diagnóstico</div>
            <h1>Sua próxima paciente está agendando com a concorrência agora.</h1>
            <p className="sub">
              3 ajustes invisíveis na sua presença digital — feitos por nós em 7
              dias — recuperam de 8 a 12 agendamentos por semana.
            </p>
            <a className="cta">
              Ver diagnóstico de 4 min <Icon name="arrow-r" size={14} />
            </a>
            <div className="cards">
              {(
                [
                  [
                    "01",
                    "PageSpeed em 31",
                    "Cada segundo a mais no carregamento reduz 7% das conversões. Otimização de imagens e lazy-load resolvem em 1 dia.",
                  ],
                  [
                    "02",
                    "WhatsApp invisível",
                    "Botão flutuante + integração direta no formulário. Resposta automática em 30s, conversão dobra.",
                  ],
                  [
                    "03",
                    "CTA que vende",
                    "Trocar 'Saiba mais' por 'Agendar avaliação gratuita' duplica cliques em estética.",
                  ],
                ] as const
              ).map(([n, h, p]) => (
                <div key={n}>
                  <div className="num">{n}</div>
                  <h3>{h}</h3>
                  <p>{p}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
        {/* Metrics */}
        <div>
          <div className="la-rail-head" style={{ marginBottom: 10 }}>
            Métricas · {m.period}
          </div>
          <div className="la-metrics">
            <div className="la-metric">
              <div className="la-metric-label">Visitas</div>
              <div className="la-metric-value">{m.visits}</div>
              <div className="la-metric-delta" style={{ color: "var(--text-muted)" }}>
                desde {m.first_visit}
              </div>
            </div>
            <div className="la-metric">
              <div className="la-metric-label">Clicks WA</div>
              <div className="la-metric-value">{m.clicks_wa}</div>
              <div className="la-metric-delta">&uarr; ativo</div>
            </div>
            <div className="la-metric">
              <div className="la-metric-label">CTR</div>
              <div className="la-metric-value">{m.ctr}%</div>
              <div className="la-metric-delta">top 10%</div>
            </div>
          </div>
        </div>

        {/* Version history */}
        <div>
          <div className="la-rail-head" style={{ marginBottom: 10 }}>
            <span>Histórico de versões</span>
            <button className="la-rail-head-action">Comparar</button>
          </div>
          <div className="la-versions">
            {lead.lp_versions.map((v) => (
              <div
                key={v.v}
                className={`la-version ${v.active ? "active" : ""}`}
              >
                <div className="la-version-v">v{v.v}</div>
                <div className="la-version-date">
                  <span className="head">{v.note}</span>
                  {v.created}
                </div>
                <button className="la-version-action">
                  {v.active ? "Ativa" : "Ativar"}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
