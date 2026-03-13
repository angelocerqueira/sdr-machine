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

  // Collect unique values for filter dropdowns
  const nichos = [...new Set(leads.map((l) => l.nicho).filter(Boolean))];
  const cidades = [...new Set(leads.map((l) => l.cidade).filter(Boolean))];

  if (loading) return <div className="text-zinc-400">Carregando...</div>;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filterNicho}
          onChange={(e) => setFilterNicho(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-300"
        >
          <option value="">Todos nichos</option>
          {nichos.map((n) => <option key={n} value={n!}>{n}</option>)}
        </select>
        <select
          value={filterCidade}
          onChange={(e) => setFilterCidade(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-300"
        >
          <option value="">Todas cidades</option>
          {cidades.map((c) => <option key={c} value={c!}>{c}</option>)}
        </select>
        <input
          type="number"
          placeholder="Score mín."
          value={filterScoreMin}
          onChange={(e) => setFilterScoreMin(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-300 w-28"
        />
      </div>

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
