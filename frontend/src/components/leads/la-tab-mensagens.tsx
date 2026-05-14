"use client";

import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "./lead-app-types";

export function LaTabMsgs({ lead }: { lead: LeadAppDetail }) {
  if (lead.messages.length === 0) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="message" size={20} />
        </div>
        <div className="state-title">Nenhuma mensagem</div>
        <div className="state-msg">
          Este lead ainda não tem mensagens de outreach geradas. Execute a etapa de outreach no pipeline.
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Message list */}
      <div className="la-msgs">
        {lead.messages.map((m) => {
          const when = m.sent_at
            ? `enviada ${new Date(m.sent_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} \u00b7 ${new Date(m.sent_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
            : m.created_at
            ? `gerada ${new Date(m.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} \u00b7 ${new Date(m.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
            : "";

          return (
            <div key={m.id} className="la-msg">
              <div className="la-msg-head">
                <span className="la-msg-label">{m.type.replace(/_/g, " ")}</span>
                {m.needs_review && (
                  <span
                    className="la-msg-badge la-msg-badge-review"
                    title="Nicho com compliance — revise antes de enviar"
                  >
                    🔍 revisar
                  </span>
                )}
                <span className="la-msg-when">{when}</span>
                <div className="la-msg-actions">
                  <button
                    className="la-msg-icon-btn"
                    title="Copiar"
                    onClick={() => navigator.clipboard.writeText(m.text)}
                  >
                    <Icon name="copy" size={14} />
                  </button>
                </div>
              </div>
              <div className="la-msg-body">{m.text}</div>
              <div className="la-msg-foot">
                <span>{m.text.length} chars</span>
                <span className="la-msg-foot-sep">&middot;</span>
                <span>~{Math.ceil(m.text.split(/\s+/).length / 130)} min leitura</span>
                {lead.telefone && (
                  <div className="la-msg-foot-send">
                    <a
                      className="btn btn-accent btn-sm"
                      href={`https://wa.me/${lead.telefone.replace(/\D/g, "")}?text=${encodeURIComponent(m.text)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon name="wa" size={14} /> Abrir no WhatsApp
                    </a>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
