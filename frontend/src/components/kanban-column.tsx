"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { KanbanCard } from "./kanban-card";
import type { Lead } from "@/lib/types";

interface KanbanColumnProps {
  id: string;
  label: string;
  leads: Lead[];
}

export function KanbanColumn({ id, label, leads }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border bg-surface min-w-[240px] w-[240px] flex flex-col transition-default ${
        isOver ? "border-accent/40 bg-accent-subtle" : "border-border"
      }`}
    >
      {/* Column header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
        <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)]">
          {label}
        </h3>
        <span className={`text-[11px] font-medium font-[family-name:var(--font-mono)] rounded-full px-2 py-0.5 ${
          leads.length > 0
            ? "bg-accent-subtle text-accent"
            : "bg-surface-raised text-text-muted"
        }`}>
          {leads.length}
        </span>
      </div>

      {/* Cards */}
      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2 p-2 flex-1 min-h-[120px]">
          {leads.map((lead) => (
            <KanbanCard key={lead.id} lead={lead} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}
