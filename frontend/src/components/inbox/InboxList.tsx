"use client";

import Link from "next/link";
import type { ConversationListItem } from "@/lib/api-inbox";

interface Props {
  items: ConversationListItem[];
  selectedId: number | null;
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `${min}min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d`;
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function InboxList({ items, selectedId }: Props) {
  if (items.length === 0) {
    return (
      <div className="inbox-empty" style={{ padding: 24 }}>
        Nenhuma conversa ainda.
      </div>
    );
  }
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {items.map((c) => {
        const active = c.id === selectedId;
        return (
          <li key={c.id}>
            <Link
              href={`/app/inbox/${c.id}`}
              style={{
                display: "block",
                padding: "12px 16px",
                borderBottom: "1px solid var(--border)",
                background: active ? "var(--surface-2)" : "transparent",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <strong style={{ fontSize: 14 }}>
                  {c.lead_nome || c.phone}
                </strong>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {fmtRelative(c.last_message_at)}
                </span>
              </div>
              <div style={{
                fontSize: 13, color: "var(--text-muted)",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {c.last_message_preview || "—"}
              </div>
              {c.unread_count > 0 && (
                <span style={{
                  display: "inline-block", marginTop: 4,
                  background: "var(--accent)", color: "white",
                  padding: "1px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                }}>
                  {c.unread_count}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
