"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { DndContext, DragEndEvent, PointerSensor, pointerWithin, useSensor, useSensors } from "@dnd-kit/core";
import { KanbanColumn } from "./kanban-column";
import { LeadSheet } from "./lead-sheet";
import { getLeadCounts, getLeadFilters, updateLead } from "@/lib/api";
import { KANBAN_COLUMNS, LEAD_PROFILE_LABEL, NICHO_LABEL } from "@/lib/types";
import type { Lead, LeadProfile, NichoCanonico } from "@/lib/types";

export interface KanbanBoardProps {
  filterNicho?: string;
  filterCidade?: string;
  filterScoreMin?: string;
  filterPerfil?: LeadProfile | "";
  filterNichoCanon?: NichoCanonico | "";
  search?: string;
  orderBy?: string;
  hideInlineFilters?: boolean;
}

export function KanbanBoard(props: KanbanBoardProps = {}) {
  const {
    filterNicho: extFilterNicho,
    filterCidade: extFilterCidade,
    filterScoreMin: extFilterScoreMin,
    filterPerfil: extFilterPerfil,
    filterNichoCanon: extFilterNichoCanon,
    search: extSearch,
    orderBy: extOrderBy,
    hideInlineFilters = false,
  } = props;

  const searchParams = useSearchParams();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [nichos, setNichos] = useState<string[]>([]);
  const [cidades, setCidades] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Internal state — used only when corresponding external prop is undefined.
  const [internalFilterNicho, setInternalFilterNicho] = useState("");
  const [internalFilterCidade, setInternalFilterCidade] = useState("");
  const [internalFilterScoreMin, setInternalFilterScoreMin] = useState("");
  const [internalFilterPerfil, setInternalFilterPerfil] = useState<LeadProfile | "">(
    (searchParams.get("perfil_lead") as LeadProfile) || "",
  );
  const [internalFilterNichoCanon, setInternalFilterNichoCanon] = useState<NichoCanonico | "">(
    (searchParams.get("nicho_canonico") as NichoCanonico) || "",
  );
  const [internalSearch, setInternalSearch] = useState("");
  const [internalOrderBy, setInternalOrderBy] = useState("score_desc");
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);

  // Effective values: external prop (if provided) > internal state.
  const filterNicho = extFilterNicho ?? internalFilterNicho;
  const filterCidade = extFilterCidade ?? internalFilterCidade;
  const filterScoreMin = extFilterScoreMin ?? internalFilterScoreMin;
  const filterPerfil = extFilterPerfil ?? internalFilterPerfil;
  const filterNichoCanon = extFilterNichoCanon ?? internalFilterNichoCanon;
  const search = extSearch ?? internalSearch;
  const orderBy = extOrderBy ?? internalOrderBy;

  // Per-column refresh triggers: bump to make a column refetch
  const [refreshKeys, setRefreshKeys] = useState<Record<string, number>>({});

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filterNicho) params.nicho = filterNicho;
      if (filterCidade) params.cidade = filterCidade;
      if (filterScoreMin) params.score_min = filterScoreMin;
      if (filterPerfil) params.perfil_lead = filterPerfil;
      if (filterNichoCanon) params.nicho_canonico = filterNichoCanon;
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
  }, [filterNicho, filterCidade, filterScoreMin, filterPerfil, filterNichoCanon, search]);

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
    "bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary font-mono focus:border-accent/50 focus:outline-none transition-default appearance-none cursor-pointer hover:border-border-strong";
  const inputClass =
    "bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted font-mono focus:border-accent/50 focus:outline-none transition-default w-28";

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
      {/* Filters (legacy inline — hidden when toolbar drives filters externally) */}
      {!hideInlineFilters && (
        <div className="flex gap-3 flex-wrap items-center">
          <span className="t-eyebrow">
            Filtros
          </span>
          <input
            type="text"
            placeholder="Buscar por nome ou telefone..."
            value={search}
            onChange={(e) => setInternalSearch(e.target.value)}
            className="bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted focus:border-accent/50 focus:outline-none transition-default w-64"
          />
          <select
            value={filterNicho}
            onChange={(e) => setInternalFilterNicho(e.target.value)}
            className={selectClass}
          >
            <option value="">Todos nichos</option>
            {nichos.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
          <select
            value={filterCidade}
            onChange={(e) => setInternalFilterCidade(e.target.value)}
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
            onChange={(e) => setInternalFilterScoreMin(e.target.value)}
            className={inputClass}
          />
          <select
            value={filterPerfil}
            onChange={(e) => setInternalFilterPerfil(e.target.value as LeadProfile | "")}
            className={selectClass}
          >
            <option value="">Todos os perfis</option>
            {(Object.entries(LEAD_PROFILE_LABEL) as [LeadProfile, string][]).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select
            value={filterNichoCanon}
            onChange={(e) => setInternalFilterNichoCanon(e.target.value as NichoCanonico | "")}
            className={selectClass}
          >
            <option value="">Todos os nichos</option>
            {(Object.entries(NICHO_LABEL) as [NichoCanonico, string][]).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select
            value={orderBy}
            onChange={(e) => setInternalOrderBy(e.target.value)}
            className={selectClass}
          >
            <option value="score_desc">Maior score</option>
            <option value="score_asc">Menor score</option>
            <option value="prioridade">Prioridade</option>
            <option value="created_desc">Mais recente</option>
            <option value="updated_desc">Atualizado recente</option>
            <option value="name_asc">Nome A-Z</option>
          </select>
        </div>
      )}

      {/* Board */}
      <DndContext sensors={sensors} collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide">
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
              filterPerfil={filterPerfil || undefined}
              filterNichoCanon={filterNichoCanon || undefined}
              search={search || undefined}
              orderBy={orderBy}
              onSelectLead={setSelectedLeadId}
            />
          ))}
        </div>
      </DndContext>
      <LeadSheet leadId={selectedLeadId} onClose={() => setSelectedLeadId(null)} />
    </div>
  );
}
