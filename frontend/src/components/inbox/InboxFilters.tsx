"use client";

import type { ConversationFilter } from "@/lib/api-inbox";

interface Props {
  value: ConversationFilter;
  onChange: (next: ConversationFilter) => void;
  search: string;
  onSearchChange: (next: string) => void;
}

const FILTERS: { key: ConversationFilter; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "unread", label: "Não lidas" },
  { key: "responded", label: "Respondidas" },
  { key: "won", label: "Ganho" },
];

export function InboxFilters({ value, onChange, search, onSearchChange }: Props) {
  return (
    <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
      <input
        type="search"
        placeholder="Buscar nome ou telefone..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          width: "100%", padding: "8px 12px", border: "1px solid var(--border)",
          borderRadius: 8, background: "var(--surface)", color: "var(--text)",
          fontSize: 14, outline: "none",
        }}
      />
      <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => onChange(f.key)}
            style={{
              padding: "4px 10px", borderRadius: 12,
              border: "1px solid var(--border)",
              background: value === f.key ? "var(--accent)" : "var(--surface)",
              color: value === f.key ? "white" : "var(--text)",
              fontSize: 12, cursor: "pointer",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
