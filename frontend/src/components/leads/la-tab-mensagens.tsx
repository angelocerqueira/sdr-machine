"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "./lead-app-types";

const TONES = [
  { key: "consultivo", label: "Consultivo" },
  { key: "direto", label: "Direto" },
  { key: "curioso", label: "Curioso" },
  { key: "urgente", label: "Urgente" },
] as const;

const MSG_WHEN = [
  "gerada 18/04 · 14:23",
  "agenda para: +3 dias",
  "agenda para: +7 dias",
];

export function LaTabMsgs({ lead }: { lead: LeadAppDetail }) {
  const [tone, setTone] = useState("consultivo");

  return (
    <div>
      {/* Composer */}
      <div className="la-composer">
        <div className="la-composer-head">
          <Icon name="sparkle" size={16} style={{ color: "var(--accent)" }} />
          <div className="la-composer-title">Gerar nova variação</div>
          <div className="la-composer-sub">Claude Haiku &middot; ~$0.003</div>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
          Usa o diagnóstico + recomendação pra gerar uma mensagem calibrada ao tom.
        </div>
        <div className="la-composer-tones">
          {TONES.map((t) => (
            <button
              key={t.key}
              className={`la-tone ${tone === t.key ? "active" : ""}`}
              onClick={() => setTone(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn btn-ghost btn-sm">Ver prompt</button>
          <button className="btn btn-primary btn-sm">
            <Icon name="sparkle" size={14} /> Gerar variação
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="la-msgs">
        {lead.messages.map((m, i) => (
          <div key={m.id} className="la-msg">
            <div className="la-msg-head">
              <span className="la-msg-label">{m.type.replace("_", " ")}</span>
              <span className="la-msg-when">{MSG_WHEN[i] ?? ""}</span>
              <div className="la-msg-actions">
                <button className="la-msg-icon-btn" title="Regenerar">
                  <Icon name="sparkle" size={14} />
                </button>
                <button className="la-msg-icon-btn" title="Copiar">
                  <Icon name="copy" size={14} />
                </button>
                <button className="la-msg-icon-btn" title="Mais">
                  <Icon name="more" size={14} />
                </button>
              </div>
            </div>
            <div
              className="la-msg-body"
              contentEditable
              suppressContentEditableWarning
            >
              {m.text}
            </div>
            <div className="la-msg-foot">
              <span>{m.text.length} chars</span>
              <span className="la-msg-foot-sep">&middot;</span>
              <span>~{Math.ceil(m.text.split(/\s+/).length / 130)} min leitura</span>
              <div className="la-msg-foot-send">
                <button className="btn btn-accent btn-sm">
                  <Icon name="wa" size={14} /> Abrir no WhatsApp
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
