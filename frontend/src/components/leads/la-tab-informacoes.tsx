"use client";

import type { LeadAppDetail } from "./lead-app-types";

const REVIEWS = [
  "Atendimento impecável. A Patrícia é super atenciosa e explica cada procedimento. Recomendo.",
  "Resultado surpreendente no primeiro procedimento. Ambiente super confortável e limpo.",
  "Profissionalismo nota 10. Demorei 2 dias pra conseguir responderem no WhatsApp, mas valeu a pena.",
];

const TIMELINE: [string, string, string][] = [
  ["16/04 · 09:41", "Scrapeada do Google Places", "scrape"],
  ["16/04 · 09:42", "Enriquecimento: 6 de 7 fontes OK", "enrich"],
  ["16/04 · 09:43", "LP gerada (v1) — Claude Sonnet", "generate"],
  ["17/04 · 10:22", "LP regenerada (v2) — hero com reviews", "generate"],
  ["18/04 · 11:08", "Re-enriquecimento: score 71 → 78", "enrich"],
  ["18/04 · 14:22", "LP regenerada (v3) — CTA reescrito", "generate"],
  ["18/04 · 14:23", "3 mensagens de outreach geradas", "outreach"],
];

export function LaTabInfo({ lead }: { lead: LeadAppDetail }) {
  return (
    <div className="la-info-grid">
      {/* Card 1: Stack detectado */}
      <div className="la-info-card">
        <div className="la-info-card-head">Stack detectado</div>
        <div className="la-tech-list">
          {lead.tech_stack.map((t, i) => {
            const warn = /jquery 1|bootstrap 3|wordpress 5/i.test(t.name);
            return (
              <span key={i} className={`la-tech ${warn ? "warn" : ""}`}>
                {t.name}
                <span className="cat">{t.category}</span>
              </span>
            );
          })}
        </div>
        <div style={{ marginTop: 14, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
          2 de 4 tecnologias desatualizadas · versões com vulnerabilidades conhecidas
        </div>
      </div>

      {/* Card 2: Top reviews */}
      <div className="la-info-card">
        <div className="la-info-card-head">Top reviews · Google Maps</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {REVIEWS.map((r, i) => (
            <div
              key={i}
              style={{
                fontSize: 12,
                color: "var(--text-body)",
                lineHeight: 1.55,
                paddingLeft: 12,
                borderLeft: "2px solid var(--border)",
              }}
            >
              &ldquo;{r}&rdquo;
            </div>
          ))}
        </div>
      </div>

      {/* Card 3: Timeline */}
      <div className="la-info-card" style={{ gridColumn: "1 / -1" }}>
        <div className="la-info-card-head">Timeline</div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            fontFamily: "var(--font-mono)",
            fontSize: 12,
          }}
        >
          {TIMELINE.map(([when, what, kind], i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "130px 1fr auto",
                gap: 14,
                alignItems: "baseline",
              }}
            >
              <div style={{ color: "var(--text-muted)" }}>{when}</div>
              <div style={{ color: "var(--text-body)", fontFamily: "var(--font-sans)" }}>
                {what}
              </div>
              <div
                style={{
                  color: "var(--text-subtle)",
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                {kind}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
