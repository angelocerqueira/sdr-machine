"use client";

import Link from "next/link";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
}

export function ConversationRail({ conversation }: Props) {
  return (
    <div style={{ padding: 16 }}>
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase",
                     letterSpacing: 0.5, marginBottom: 8 }}>
          Lead
        </h3>
        <div style={{ fontSize: 14 }}>
          Telefone: <strong>{conversation.phone}</strong>
        </div>
        <Link
          href={`/app/leads/${conversation.lead_id}`}
          style={{
            display: "inline-block", marginTop: 12,
            padding: "6px 12px", borderRadius: 8,
            background: "var(--accent)", color: "white",
            textDecoration: "none", fontSize: 13,
          }}
        >
          Abrir Lead →
        </Link>
      </section>
      <section>
        <h3 style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase",
                     letterSpacing: 0.5, marginBottom: 8 }}>
          Conversa
        </h3>
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
          {conversation.messages.length} mensagens<br />
          Criada em {new Date(conversation.created_at).toLocaleString("pt-BR")}
        </div>
      </section>
    </div>
  );
}
