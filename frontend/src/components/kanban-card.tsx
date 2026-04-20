"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { ProfileBadge } from "@/components/ui/profile-badge";
import type { Lead } from "@/lib/types";

interface KanbanCardProps {
  lead: Lead;
  onSelect: (id: number) => void;
}

export function KanbanCard({ lead, onSelect }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: lead.id,
    data: { lead },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
  };

  const hasError = lead.status.endsWith("_failed");
  const score = lead.opportunity_score ?? 0;
  const scoreClass = score >= 80 ? "score-high" : score >= 50 ? "score-mid" : "score-low";
  const borderColor = score >= 80 ? "border-l-score-high" : score >= 50 ? "border-l-score-mid" : "border-l-score-low";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`group rounded-md border border-border bg-surface-raised p-3 cursor-grab active:cursor-grabbing transition-default border-l-2 hover:border-border-strong ${borderColor} ${
        isDragging ? "kanban-card-dragging" : ""
      } ${hasError ? "border-danger/30" : ""}`}
    >
      <div onClick={() => onSelect(lead.id)} className="min-w-0">
        <p className="text-[13px] font-medium text-text truncate">{lead.nome}</p>
        {lead.perfil_lead && (
          <div className="mt-1.5">
            <ProfileBadge profile={lead.perfil_lead} size="sm" />
          </div>
        )}
        <div className="flex items-center justify-between mt-2">
          <span className="text-[11px] text-text-muted font-mono truncate mr-2">{lead.nicho}</span>
          <span className={`tooltip text-[11px] font-semibold font-mono tabular-nums shrink-0 ${scoreClass}`}>
            {lead.opportunity_score ?? "\u2014"}
            {lead.opportunity_reasons?.length > 0 && (
              <span className="tooltip-content">
                {lead.opportunity_reasons.slice(0, 4).map(r => r.replace(/^\[[A-Z_]+\]\s*/, "")).join(" \u00b7 ")}
              </span>
            )}
          </span>
        </div>
        {lead.rating && (
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className="text-[10px] text-text-muted font-mono tabular-nums">{lead.rating}</span>
            <svg className="w-2.5 h-2.5 text-warning shrink-0" viewBox="0 0 12 12" fill="currentColor">
              <path d="M6 0l1.8 3.6L12 4.2l-3 2.9.7 4.1L6 9.1 2.3 11.2l.7-4.1-3-2.9 4.2-.6z" />
            </svg>
            <span className="text-[10px] text-text-muted font-mono truncate">{lead.cidade}</span>
          </div>
        )}
        {hasError && (
          <p className="text-[10px] text-danger mt-1.5 font-mono">Erro na fase</p>
        )}
      </div>
    </div>
  );
}
