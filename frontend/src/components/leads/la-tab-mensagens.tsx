"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { rateMessage, trackMessageClick, trackMessageCopy } from "@/lib/api";
import type { LeadAppDetail } from "./lead-app-types";

type LeadMessage = LeadAppDetail["messages"][number];

export function LaTabMsgs({ lead }: { lead: LeadAppDetail }) {
  // Local overlay map keyed by message id — stores rating updates done in this component.
  // We re-derive `messages` from props on every render so a new lead / refreshed messages
  // immediately reflect, while still keeping optimistic rating updates between fetches.
  const [ratingOverrides, setRatingOverrides] = useState<Record<number, number | null>>({});
  const [overridesLeadId, setOverridesLeadId] = useState<number>(lead.id);

  // Reset overrides when the active lead changes (derive-from-props pattern, no effect needed).
  if (overridesLeadId !== lead.id) {
    setOverridesLeadId(lead.id);
    setRatingOverrides({});
  }

  const messages: LeadMessage[] = lead.messages.map((m) =>
    m.id in ratingOverrides ? { ...m, manual_rating: ratingOverrides[m.id] } : m
  );

  if (messages.length === 0) {
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

  const handleCopy = (msgId: number, text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
    trackMessageCopy(lead.id, msgId).catch(() => {});
  };

  const handleClick = (msgId: number) => {
    trackMessageClick(lead.id, msgId).catch(() => {});
  };

  const handleRate = async (msgId: number, rating: number) => {
    try {
      const res = await rateMessage(lead.id, msgId, rating);
      setRatingOverrides((prev) => ({ ...prev, [msgId]: res.manual_rating }));
    } catch (err) {
      console.error("Failed to rate message", err);
    }
  };

  return (
    <div>
      {/* Message list */}
      <div className="la-msgs">
        {messages.map((m) => {
          const when = m.sent_at
            ? `enviada ${new Date(m.sent_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} · ${new Date(m.sent_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
            : m.created_at
            ? `gerada ${new Date(m.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} · ${new Date(m.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
            : "";

          const ratingUp = m.manual_rating === 1;
          const ratingDown = m.manual_rating === -1;

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
                    type="button"
                    onClick={() => handleCopy(m.id, m.text)}
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
                <div className="la-msg-rate">
                  <button
                    className={`la-msg-rate-btn ${ratingUp ? "is-active" : ""}`}
                    title="Gostei"
                    type="button"
                    onClick={() => handleRate(m.id, ratingUp ? 0 : 1)}
                    aria-pressed={ratingUp}
                  >
                    <span aria-hidden>👍</span>
                  </button>
                  <button
                    className={`la-msg-rate-btn ${ratingDown ? "is-active" : ""}`}
                    title="Não gostei"
                    type="button"
                    onClick={() => handleRate(m.id, ratingDown ? 0 : -1)}
                    aria-pressed={ratingDown}
                  >
                    <span aria-hidden>👎</span>
                  </button>
                </div>
                {lead.telefone && (
                  <div className="la-msg-foot-send">
                    <a
                      className="btn btn-accent btn-sm"
                      href={`https://wa.me/${lead.telefone.replace(/\D/g, "")}?text=${encodeURIComponent(m.text)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => handleClick(m.id)}
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
