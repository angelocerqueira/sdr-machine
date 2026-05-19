import Link from "next/link";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
}

const STATUS_LABELS: Record<string, string> = {
  scraped: "scrapeado",
  enriched: "enriquecido",
  lp_generated: "LP gerada",
  outreach_ready: "pronto",
  outreach_sent: "abordado",
  responded: "respondeu",
  in_call: "em call",
  closed: "fechado",
  delivered: "entregue",
};

function formatPhone(phone: string): string {
  // 5511982956611 → (11) 98295-6611  (BR, 12 ou 13 dígitos)
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 13 && digits.startsWith("55")) {
    return `(${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`;
  }
  if (digits.length === 12 && digits.startsWith("55")) {
    return `(${digits.slice(2, 4)}) ${digits.slice(4, 8)}-${digits.slice(8)}`;
  }
  return phone;
}

function initials(name: string): string {
  const t = name.trim();
  if (!t) return "?";
  const parts = t.split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]).join("").toUpperCase();
}

export function ConversationHeader({ conversation }: Props) {
  const displayName = conversation.lead_nome || `+${conversation.phone}`;
  const statusLabel = STATUS_LABELS[conversation.lead_status] || conversation.lead_status;

  return (
    <header className="inbox-conv-header">
      <div className="inbox-conv-header-avatar" aria-hidden>
        {initials(conversation.lead_nome)}
      </div>
      <div className="inbox-conv-header-meta">
        <div className="inbox-conv-header-name">{displayName}</div>
        <div className="inbox-conv-header-sub">
          <span className={`inbox-conv-header-status status-${conversation.lead_status}`}>
            {statusLabel}
          </span>
          <span className="inbox-conv-header-phone">{formatPhone(conversation.phone)}</span>
        </div>
      </div>
      <Link
        href={`/app/leads/${conversation.lead_id}`}
        className="inbox-conv-header-action"
      >
        Abrir Lead →
      </Link>
    </header>
  );
}
