"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Link from "next/link";
import type { Lead } from "@/lib/types";

interface KanbanCardProps {
  lead: Lead;
}

export function KanbanCard({ lead }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
    data: { lead },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const hasError = lead.status.endsWith("_failed");
  const scoreColor =
    (lead.opportunity_score ?? 0) >= 60 ? "text-green-400" :
    (lead.opportunity_score ?? 0) >= 40 ? "text-yellow-400" : "text-zinc-400";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`bg-zinc-800 border rounded-lg p-3 cursor-grab active:cursor-grabbing ${
        hasError ? "border-red-500/50" : "border-zinc-700"
      }`}
    >
      <Link href={`/leads/${lead.id}`} className="block">
        <p className="text-sm font-medium text-white truncate">{lead.nome}</p>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-xs text-zinc-400">{lead.nicho}</span>
          <span className={`text-xs font-mono ${scoreColor}`}>
            {lead.opportunity_score ?? "—"}
          </span>
        </div>
        {lead.rating && (
          <p className="text-xs text-zinc-500 mt-1">{lead.rating}⭐ · {lead.cidade}</p>
        )}
        {hasError && <p className="text-xs text-red-400 mt-1">Erro na fase</p>}
      </Link>
    </div>
  );
}
