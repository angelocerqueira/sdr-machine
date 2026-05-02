"use client";

import { useCallback, useEffect, useRef, useState, type MouseEvent } from "react";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Icon } from "@/components/ui";
import { runEnrich } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { buildWaLink } from "@/lib/format";
import { deriveSignals } from "@/lib/pipeline-signals";
import type { Lead } from "@/lib/types";

interface KanbanCardProps {
  lead: Lead;
  onSelect: (id: number) => void;
}

function scoreClass(score: number): "high" | "mid" | "low" {
  if (score >= 80) return "high";
  if (score >= 50) return "mid";
  return "low";
}

const MAX_VISIBLE_SIGNALS = 3;

export function KanbanCard({ lead, onSelect }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: lead.id,
    data: { lead },
  });
  const { toast } = useToast();
  const [enriching, setEnriching] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const style = transform ? { transform: CSS.Transform.toString(transform) } : undefined;

  const score = lead.opportunity_score ?? 0;
  const sc = scoreClass(score);
  const isHot = score >= 80;
  const hasError = lead.status.endsWith("_failed");

  const signals = deriveSignals(lead.opportunity_reasons);
  const visibleSignals = signals.slice(0, MAX_VISIBLE_SIGNALS);
  const extraSignals = signals.length - visibleSignals.length;

  const waLink = buildWaLink(lead.telefone);

  const stop = (e: MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
  };

  const handleEnrich = useCallback(
    async (e: MouseEvent) => {
      stop(e);
      if (enriching) return;
      setEnriching(true);
      try {
        await runEnrich({ lead_ids: [lead.id], force_providers: [] });
        toast(`Enriquecimento iniciado para ${lead.nome}.`, { variant: "success" });
      } catch (err) {
        toast(`Erro: ${err instanceof Error ? err.message : "falha ao enriquecer"}`, {
          variant: "error",
        });
      } finally {
        // Card may have unmounted (e.g. lead moved to another column after
        // optimistic dnd update) by the time the request returns.
        if (mountedRef.current) setEnriching(false);
      }
    },
    [enriching, lead.id, lead.nome, toast],
  );

  const handleWa = (e: MouseEvent) => {
    stop(e);
    if (waLink) window.open(waLink, "_blank", "noopener,noreferrer");
  };

  const handleSelect = () => onSelect(lead.id);

  return (
    <article
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={handleSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleSelect();
        }
      }}
      aria-label={`${lead.nome} — score ${score}`}
      className={`pl-card pl-card-${sc}${isHot ? " pl-card-hot" : ""}${
        isDragging ? " kanban-card-dragging" : ""
      }${hasError ? " pl-card-error" : ""}`}
    >
      <div className="pl-card-rail" />
      <div className="pl-card-body">
        <div className="pl-card-head">
          <h3 className="pl-card-name">{lead.nome}</h3>
          <div
            className={`pl-card-score pl-card-score-${sc}`}
            aria-label={`Score ${score} de 100`}
          >
            {lead.opportunity_score ?? "—"}
          </div>
        </div>

        <div className="pl-card-meta">
          {lead.nicho && <span className="pl-card-meta-niche">{lead.nicho}</span>}
          {lead.rating != null && (
            <>
              <span className="pl-card-meta-dot">·</span>
              <span className="pl-card-meta-rating">
                <span className="pl-card-meta-star">★</span>
                <span>{lead.rating.toFixed(1).replace(".", ",")}</span>
                {lead.reviews_count > 0 && (
                  <span className="pl-card-meta-reviews">({lead.reviews_count})</span>
                )}
              </span>
            </>
          )}
          {lead.cidade && (
            <>
              <span className="pl-card-meta-dot">·</span>
              <span className="pl-card-meta-city">{lead.cidade}</span>
            </>
          )}
        </div>

        {visibleSignals.length > 0 && (
          <div className="pl-card-signals">
            {visibleSignals.map((s) => (
              <span
                key={s.key}
                className={`pl-signal pl-signal-${s.tone}`}
                aria-label={`Sinal: ${s.label}`}
              >
                {s.tone === "danger" && <span className="pl-signal-dot" />}
                {s.label}
              </span>
            ))}
            {extraSignals > 0 && (
              <span className="pl-signal pl-signal-muted">+{extraSignals}</span>
            )}
          </div>
        )}

        {hasError && (
          <div className="pl-signal pl-signal-danger" style={{ alignSelf: "flex-start" }}>
            <span className="pl-signal-dot" />
            Erro na fase
          </div>
        )}

        <div className="pl-card-actions" onClick={stop}>
          <button
            type="button"
            className="pl-card-action"
            onClick={handleEnrich}
            disabled={enriching}
            title={enriching ? "Enriquecendo..." : "Enriquecer"}
          >
            <Icon name="sparkle" size={13} />
            {enriching ? "Enriquecendo" : "Enriquecer"}
          </button>
          <button
            type="button"
            className="pl-card-action pl-card-action-icon"
            onClick={handleWa}
            disabled={!waLink}
            title={waLink ? `Abrir WhatsApp (${lead.telefone})` : "Sem telefone"}
            aria-label="Abrir WhatsApp"
          >
            <Icon name="phone" size={13} />
          </button>
          <button
            type="button"
            className="pl-card-action pl-card-action-icon"
            disabled
            title="Cadência de email em breve"
            aria-label="Email"
          >
            <Icon name="mail" size={13} />
          </button>
          <button
            type="button"
            className="pl-card-action pl-card-action-icon pl-card-action-more"
            onClick={(e) => {
              stop(e);
              onSelect(lead.id);
            }}
            title="Ver detalhes"
            aria-label="Ver detalhes"
          >
            <Icon name="more" size={13} />
          </button>
        </div>
      </div>
    </article>
  );
}
