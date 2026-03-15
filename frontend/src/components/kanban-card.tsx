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
  };

  const hasError = lead.status.endsWith("_failed");
  const score = lead.opportunity_score ?? 0;
  const scoreClass = score >= 60 ? "score-high" : score >= 40 ? "score-mid" : "score-low";
  const borderAccent = score >= 60 ? "border-l-accent" : score >= 40 ? "border-l-warning" : "border-l-border";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`group rounded-lg border border-border bg-surface-raised p-3 cursor-grab active:cursor-grabbing card-glow transition-default border-l-2 ${borderAccent} ${
        isDragging ? "kanban-card-dragging" : ""
      } ${hasError ? "border-danger/30" : ""}`}
    >
      <Link href={`/leads/${lead.id}`} className="block">
        <p className="text-[13px] font-medium text-text truncate">{lead.nome}</p>
        <div className="flex items-center justify-between mt-2">
          <span className="text-[11px] text-text-muted font-[family-name:var(--font-mono)]">{lead.nicho}</span>
          <span className={`text-[11px] font-semibold font-[family-name:var(--font-mono)] ${scoreClass}`}>
            {lead.opportunity_score ?? "—"}
          </span>
        </div>
        {lead.rating && (
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className="text-[10px] text-text-muted">{lead.rating}</span>
            <svg className="w-2.5 h-2.5 text-warning" viewBox="0 0 12 12" fill="currentColor">
              <path d="M6 0l1.8 3.6L12 4.2l-3 2.9.7 4.1L6 9.1 2.3 11.2l.7-4.1-3-2.9 4.2-.6z" />
            </svg>
            <span className="text-[10px] text-text-muted">{lead.cidade}</span>
          </div>
        )}
        {hasError && (
          <p className="text-[10px] text-danger mt-1.5 font-[family-name:var(--font-mono)]">Erro na fase</p>
        )}
      </Link>
    </div>
  );
}
