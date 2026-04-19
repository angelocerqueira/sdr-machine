"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { updateLead } from "@/lib/api";
import { scoreClass } from "./lead-app-mock";
import type { LeadAppDetail } from "./lead-app-types";

interface LaRailProps {
  lead: LeadAppDetail;
  onLeadUpdated?: () => void;
}

const NIVEL_LABELS: Record<string, string> = {
  lp: "Landing Page",
  automacao_basica: "Automação Básica",
  mapa_automacoes: "Mapa de Automações",
  vertical_os: "Vertical OS",
};

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

/* ─── Section 2: Recommendation (ServiceLevels) ─── */
function LaRailReco({ lead }: LaRailProps) {
  const sl = lead.service_levels;
  const nivel = sl?.nivel_recomendado || lead.recommendation.level;
  const label = NIVEL_LABELS[nivel] || lead.recommendation.label;

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Recomendação</span>
      </div>
      <div className="la-reco">
        <div className="la-reco-head">Nível recomendado</div>
        <div className="la-reco-title">{label}</div>
        {sl?.resumo_executivo && (
          <div className="la-reco-body">{sl.resumo_executivo}</div>
        )}
        {sl && nivel && sl[nivel as keyof typeof sl] && typeof sl[nivel as keyof typeof sl] === "object" && (
          (() => {
            const data = sl[nivel as "lp" | "automacao_basica" | "mapa_automacoes" | "vertical_os"];
            if (!data || typeof data !== "object" || !("sinais" in data)) return null;
            return (
              <>
                {data.sinais.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-subtle)", marginBottom: 4 }}>
                      Sinais
                    </div>
                    <ul style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5, paddingLeft: 14, margin: 0 }}>
                      {data.sinais.slice(0, 4).map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                {data.oportunidades.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-subtle)", marginBottom: 4 }}>
                      Oportunidades
                    </div>
                    <ul style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5, paddingLeft: 14, margin: 0 }}>
                      {data.oportunidades.slice(0, 4).map((o, i) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>
                )}
              </>
            );
          })()
        )}
      </div>
    </div>
  );
}

/* ─── Section 3: Details (KV grid) — editable ─── */

type EditableField = "email" | "endereco" | "cidade" | "nicho" | "telefone";

const EDITABLE_FIELDS: { label: string; field: EditableField }[] = [
  { label: "Email", field: "email" },
  { label: "Telefone", field: "telefone" },
  { label: "Endereço", field: "endereco" },
  { label: "Cidade", field: "cidade" },
  { label: "Nicho", field: "nicho" },
];

const READONLY_ROWS: { label: string; getValue: (lead: LeadAppDetail) => string }[] = [
  { label: "CNPJ", getValue: (l) => l.cnpj },
  { label: "Razão", getValue: (l) => l.razao_social },
  { label: "Porte", getValue: (l) => l.porte },
  { label: "CNAE", getValue: (l) => l.cnae },
  { label: "Sócios", getValue: (l) => l.socios.map((s) => s.nome).join(", ") },
];

function LaRailDetails({ lead, onLeadUpdated }: LaRailProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Record<EditableField, string>>({
    email: lead.email,
    telefone: lead.telefone,
    endereco: lead.endereco,
    cidade: lead.cidade,
    nicho: lead.nicho,
  });

  const startEditing = () => {
    setDraft({
      email: lead.email,
      telefone: lead.telefone,
      endereco: lead.endereco,
      cidade: lead.cidade,
      nicho: lead.nicho,
    });
    setEditing(true);
  };

  const cancel = () => setEditing(false);

  const save = async () => {
    const changed: Record<string, string> = {};
    for (const { field } of EDITABLE_FIELDS) {
      if (draft[field] !== lead[field]) {
        changed[field] = draft[field];
      }
    }
    if (Object.keys(changed).length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await updateLead(lead.id, changed);
      setEditing(false);
      onLeadUpdated?.();
    } catch (e) {
      console.error("Erro ao salvar:", e);
    } finally {
      setSaving(false);
    }
  };

  const allRows = [
    ...EDITABLE_FIELDS.map(({ label, field }) => ({ label, value: lead[field], editable: true, field })),
    ...READONLY_ROWS.map(({ label, getValue }) => ({ label, value: getValue(lead), editable: false, field: undefined })),
  ];

  const hasData = allRows.some((r) => r.value);

  if (!hasData) return null;

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Cadastro</span>
        {!editing ? (
          <button
            onClick={startEditing}
            style={{
              all: "unset",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 3,
              fontSize: 10,
              textTransform: "none",
              letterSpacing: 0,
              color: "var(--accent)",
            }}
          >
            <Icon name="settings" size={11} /> Editar
          </button>
        ) : (
          <div style={{ display: "flex", gap: 4 }}>
            <button
              onClick={save}
              disabled={saving}
              style={{
                all: "unset",
                cursor: saving ? "wait" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 2,
                fontSize: 10,
                color: "var(--ok)",
                opacity: saving ? 0.5 : 1,
              }}
            >
              <Icon name="check" size={11} /> Salvar
            </button>
            <button
              onClick={cancel}
              disabled={saving}
              style={{
                all: "unset",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 2,
                fontSize: 10,
                color: "var(--text-muted)",
              }}
            >
              <Icon name="x" size={11} />
            </button>
          </div>
        )}
      </div>
      <dl className="la-kv">
        {allRows.map(({ label, value, editable, field }) => {
          if (!editing && !value) return null;
          return (
            <div key={label} className="la-kv-row">
              <dt>{label}</dt>
              {editing && editable && field ? (
                <dd>
                  <input
                    type="text"
                    value={draft[field as EditableField]}
                    onChange={(e) => setDraft((d) => ({ ...d, [field]: e.target.value }))}
                    style={{
                      width: "100%",
                      fontSize: 12,
                      padding: "3px 6px",
                      border: "1px solid var(--border)",
                      borderRadius: 4,
                      background: "var(--surface-raised)",
                      color: "var(--text-body)",
                      outline: "none",
                      fontFamily: "inherit",
                    }}
                  />
                </dd>
              ) : (
                <dd style={{ fontSize: 12 }}>{value || "\u2014"}</dd>
              )}
            </div>
          );
        })}
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
export function LaRail({ lead, onLeadUpdated }: LaRailProps) {
  return (
    <aside className="la-rail">
      <LaRailScore lead={lead} />
      <LaRailReco lead={lead} />
      <LaRailDetails lead={lead} onLeadUpdated={onLeadUpdated} />
      <LaRailSources lead={lead} />
    </aside>
  );
}
