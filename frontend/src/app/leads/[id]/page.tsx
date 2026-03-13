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

  if (!lead) return <div className="text-zinc-400">Carregando...</div>;

  const initialMsg = messages.find((m) => m.type === "initial");
  const whatsappLink = initialMsg?.whatsapp_link || "";

  return (
    <div className="max-w-4xl space-y-6">
      <button onClick={() => router.back()} className="text-sm text-zinc-400 hover:text-white">
        ← Voltar
      </button>
      <LeadDetail lead={lead} />
      {whatsappLink && lead.status === "outreach_ready" && (
        <WhatsAppButton whatsappLink={whatsappLink} onMarkSent={handleMarkSent} />
      )}

      {/* Outreach Messages */}
      {messages.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-3">Mensagens de Outreach</h3>
          <div className="space-y-4">
            {messages.map((msg) => (
              <div key={msg.id} className="bg-zinc-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-zinc-400 uppercase">{msg.type.replace("_", " ")}</span>
                  {msg.sent_at && <span className="text-xs text-green-400">Enviada</span>}
                </div>
                <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-sans">{msg.message_text}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
