"use client";

import { useState, useEffect, useCallback } from "react";
import { DndContext, DragEndEvent, pointerWithin } from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import { getLeadCounts, updateLead } from "@/lib/api";
import { KANBAN_COLUMNS } from "@/lib/types";
import type { Lead } from "@/lib/types";

export function KanbanBoard() {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [filterNicho, setFilterNicho] = useState("");
  const [filterCidade, setFilterCidade] = useState("");
  const [filterScoreMin, setFilterScoreMin] = useState("");

  // Per-column refresh triggers: bump to make a column refetch
  const [refreshKeys, setRefreshKeys] = useState<Record<string, number>>({});

  const fetchCounts = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filterNicho) params.nicho = filterNicho;
      if (filterCidade) params.cidade = filterCidade;
      if (filterScoreMin) params.score_min = filterScoreMin;
      const data = await getLeadCounts(params);
      setCounts(data);
    } catch (err) {
      console.error("Erro ao carregar contagens:", err);
    } finally {
      setLoading(false);
    }
  }, [filterNicho, filterCidade, filterScoreMin]);

  useEffect(() => {
    setLoading(true);
    fetchCounts();
  }, [fetchCounts]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const lead = active.data.current?.lead as Lead | undefined;
    const newStatus = over.id as string;

    if (!lead || lead.status === newStatus) return;

    const sourceStatus = lead.status;

    // Optimistic count update
    setCounts((prev) => ({
      ...prev,
      [sourceStatus]: Math.max(0, (prev[sourceStatus] || 0) - 1),
      [newStatus]: (prev[newStatus] || 0) + 1,
    }));

    try {
      await updateLead(lead.id, { status: newStatus });
    } catch {
      // Rollback counts
      setCounts((prev) => ({
        ...prev,
        [sourceStatus]: (prev[sourceStatus] || 0) + 1,
        [newStatus]: Math.max(0, (prev[newStatus] || 0) - 1),
      }));
    }

    // Refresh both affected columns
    setRefreshKeys((prev) => ({
      ...prev,
      [sourceStatus]: (prev[sourceStatus] || 0) + 1,
      [newStatus]: (prev[newStatus] || 0) + 1,
    }));
  };

  const inputClass =
    "bg-surface-raised border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted focus:border-accent/50 focus:outline-none transition-default w-28 font-[family-name:var(--font-mono)]";

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <span className="text-[11px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)]">
          Filtros
        </span>
        <input
          type="text"
          placeholder="Nicho"
          value={filterNicho}
          onChange={(e) => setFilterNicho(e.target.value)}
          className={inputClass}
        />
        <input
          type="text"
          placeholder="Cidade"
          value={filterCidade}
          onChange={(e) => setFilterCidade(e.target.value)}
          className={inputClass}
        />
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
              count={counts[col.id] || 0}
              refreshKey={refreshKeys[col.id] || 0}
              filterNicho={filterNicho || undefined}
              filterCidade={filterCidade || undefined}
              filterScoreMin={filterScoreMin || undefined}
            />
          ))}
        </div>
      </DndContext>
    </div>
  );
}
