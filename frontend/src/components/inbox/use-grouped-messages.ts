import { useMemo } from "react";
import type { Message } from "@/lib/api-inbox";

export type GroupedItem =
  | { kind: "divider"; date: Date; label: string }
  | { kind: "message"; message: Message };

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function dayLabel(d: Date): string {
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (dayKey(d) === dayKey(today)) return "Hoje";
  if (dayKey(d) === dayKey(yesterday)) return "Ontem";

  return d.toLocaleDateString("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}

function messageDate(m: Message): Date | null {
  const iso = m.direction === "in" ? m.received_at : m.sent_at;
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

export function useGroupedMessages(messages: Message[]): GroupedItem[] {
  return useMemo(() => {
    const out: GroupedItem[] = [];
    let lastKey: string | null = null;

    for (const m of messages) {
      const d = messageDate(m);
      if (!d) {
        out.push({ kind: "message", message: m });
        continue;
      }
      const k = dayKey(d);
      if (k !== lastKey) {
        out.push({ kind: "divider", date: d, label: dayLabel(d) });
        lastKey = k;
      }
      out.push({ kind: "message", message: m });
    }

    return out;
  }, [messages]);
}
