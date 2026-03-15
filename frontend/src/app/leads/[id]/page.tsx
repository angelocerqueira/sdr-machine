"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getLead, updateLead, getLeadMessages } from "@/lib/api";
import { LeadDetail } from "@/components/lead-detail";
import { WhatsAppButton } from "@/components/whatsapp-button";
import type { Lead, OutreachMessage } from "@/lib/types";

export default function LeadPage() {
  const params = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<OutreachMessage[]>([]);

  useEffect(() => {
    const id = Number(params.id);
    if (id) {
      getLead(id).then(setLead);
      getLeadMessages(id).then(setMessages).catch(() => {});
    }
  }, [params.id]);

  const handleMarkSent = async () => {
    if (!lead) return;
    const updated = await updateLead(lead.id, { status: "outreach_sent" });
    setLead(updated);
  };

  if (!lead) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  const initialMsg = messages.find((m) => m.type === "initial");
  const whatsappLink = initialMsg?.whatsapp_link || "";

  return (
    <div className="max-w-4xl space-y-6">
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text transition-default group"
      >
        <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <path d="M10 3L5 8l5 5" />
        </svg>
        Voltar
      </button>

      <LeadDetail lead={lead} />

      {whatsappLink && lead.status === "outreach_ready" && (
        <WhatsAppButton whatsappLink={whatsappLink} onMarkSent={handleMarkSent} />
      )}

      {/* Outreach Messages */}
      {messages.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-4">
            Mensagens de Outreach
          </h3>
          <div className="space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className="rounded-lg border border-border-subtle bg-surface-raised p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="status-pill bg-surface-overlay text-text-muted">
                    {msg.type.replace("_", " ")}
                  </span>
                  {msg.sent_at && (
                    <span className="inline-flex items-center gap-1.5 text-[11px] text-accent font-[family-name:var(--font-mono)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                      Enviada
                    </span>
                  )}
                </div>
                <pre className="text-[13px] text-text-secondary whitespace-pre-wrap font-[family-name:var(--font-body)] leading-relaxed">
                  {msg.message_text}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
