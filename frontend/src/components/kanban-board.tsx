"use client";

import { useState, useEffect, useCallback } from "react";
import { DndContext, DragEndEvent, pointerWithin } from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import { getLeads, updateLead } from "@/lib/api";
import { KANBAN_COLUMNS } from "@/lib/types";
import type { Lead } from "@/lib/types";

export function KanbanBoard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterNicho, setFilterNicho] = useState("");
  const [filterCidade, setFilterCidade] = useState("");
  const [filterScoreMin, setFilterScoreMin] = useState("");

  const fetchLeads = useCallback(async () => {
    const params: Record<string, string> = { per_page: "500" };
    if (filterNicho) params.nicho = filterNicho;
    if (filterCidade) params.cidade = filterCidade;
    if (filterScoreMin) params.score_min = filterScoreMin;
    const data = await getLeads(params);
    setLeads(data.items);
    setLoading(false);
  }, [filterNicho, filterCidade, filterScoreMin]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const leadId = active.id as number;
    const newStatus = over.id as string;

    const lead = leads.find((l) => l.id === leadId);
    if (!lead || lead.status === newStatus) return;

    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
    );

    try {
      await updateLead(leadId, { status: newStatus });
    } catch {
      fetchLeads();
    }
  };

  const nichos = [...new Set(leads.map((l) => l.nicho).filter(Boolean))];
  const cidades = [...new Set(leads.map((l) => l.cidade).filter(Boolean))];

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  const selectClass =
    "bg-surface-raised border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-secondary focus:border-accent/50 focus:outline-none transition-default appearance-none cursor-pointer hover:border-text-muted";
  const inputClass =
    "bg-surface-raised border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted focus:border-accent/50 focus:outline-none transition-default w-28 font-[family-name:var(--font-mono)]";

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <span className="text-[11px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)]">Filtros</span>
        <select value={filterNicho} onChange={(e) => setFilterNicho(e.target.value)} className={selectClass}>
          <option value="">Todos nichos</option>
          {nichos.map((n) => <option key={n} value={n!}>{n}</option>)}
        </select>
        <select value={filterCidade} onChange={(e) => setFilterCidade(e.target.value)} className={selectClass}>
          <option value="">Todas cidades</option>
          {cidades.map((c) => <option key={c} value={c!}>{c}</option>)}
        </select>
        <input
          type="number"
          placeholder="Score min"
          value={filterScoreMin}
          onChange={(e) => setFilterScoreMin(e.target.value)}
          className={inputClass}
        />
      </div>

      {/* Board */}
      <DndContext collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4">
          {KANBAN_COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              label={col.label}
              leads={leads.filter((l) => l.status === col.id)}
            />
          ))}
        </div>
      </DndContext>
    </div>
  );
}
