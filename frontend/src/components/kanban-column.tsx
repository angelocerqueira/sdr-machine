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
      className={`bg-zinc-900 border border-zinc-800 rounded-xl p-3 min-w-[220px] w-[220px] flex flex-col ${
        isOver ? "ring-2 ring-blue-500/50" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">{label}</h3>
        <span className="text-xs text-zinc-500 bg-zinc-800 rounded-full px-2 py-0.5">{leads.length}</span>
      </div>
      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2 flex-1 min-h-[100px]">
          {leads.map((lead) => (
            <KanbanCard key={lead.id} lead={lead} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}
