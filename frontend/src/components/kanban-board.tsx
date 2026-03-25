"use client";

import { useState, useEffect, useCallback } from "react";
import { DndContext, DragEndEvent, PointerSensor, pointerWithin, useSensor, useSensors } from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import { LeadSheet } from "./lead-sheet";
import { getLeadCounts, getLeadFilters, updateLead } from "@/lib/api";
import { KANBAN_COLUMNS } from "@/lib/types";
import type { Lead } from "@/lib/types";

export function KanbanBoard() {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [nichos, setNichos] = useState<string[]>([]);
  const [cidades, setCidades] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterNicho, setFilterNicho] = useState("");
  const [filterCidade, setFilterCidade] = useState("");
  const [filterScoreMin, setFilterScoreMin] = useState("");
  const [search, setSearch] = useState("");
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);

  // Per-column refresh triggers: bump to make a column refetch
  const [refreshKeys, setRefreshKeys] = useState<Record<string, number>>({});

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filterNicho) params.nicho = filterNicho;
      if (filterCidade) params.cidade = filterCidade;
      if (filterScoreMin) params.score_min = filterScoreMin;
      if (search) params.search = search;

      const [countsData, filtersData] = await Promise.all([
        getLeadCounts(params),
        getLeadFilters().catch(() => null),
      ]);

      setCounts(countsData);
      if (filtersData) {
        setNichos(filtersData.nichos);
        setCidades(filtersData.cidades);
      }
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
    } finally {
      setLoading(false);
    }
  }, [filterNicho, filterCidade, filterScoreMin, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  const selectClass =
    "bg-surface-raised border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-secondary focus:border-accent/50 focus:outline-none transition-default appearance-none cursor-pointer hover:border-text-muted";
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
          placeholder="Buscar por nome ou telefone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-surface-raised border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted focus:border-accent/50 focus:outline-none transition-default w-64"
        />
        <select
          value={filterNicho}
          onChange={(e) => setFilterNicho(e.target.value)}
          className={selectClass}
        >
          <option value="">Todos nichos</option>
          {nichos.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
        <select
          value={filterCidade}
          onChange={(e) => setFilterCidade(e.target.value)}
          className={selectClass}
        >
          <option value="">Todas cidades</option>
          {cidades.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
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
      <DndContext sensors={sensors} collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
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
              search={search || undefined}
              orderBy="score_desc"
              onSelectLead={setSelectedLeadId}
            />
          ))}
        </div>
      </DndContext>
      <LeadSheet leadId={selectedLeadId} onClose={() => setSelectedLeadId(null)} />
    </div>
  );
}
