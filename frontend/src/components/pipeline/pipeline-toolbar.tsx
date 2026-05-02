"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getLeadFilters } from "@/lib/api";
import { LEAD_PROFILE_LABEL, NICHO_LABEL } from "@/lib/types";
import type { LeadProfile, NichoCanonico } from "@/lib/types";
import { track } from "@/lib/telemetry";

const SELECT_CLASS =
  "bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary font-mono focus:border-accent/50 focus:outline-none transition-default appearance-none cursor-pointer hover:border-border-strong";
const INPUT_CLASS =
  "bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted font-mono focus:border-accent/50 focus:outline-none transition-default w-28";
const SEARCH_CLASS =
  "bg-surface-raised border border-border rounded-md px-3 py-1.5 text-[13px] text-text-secondary placeholder:text-text-muted focus:border-accent/50 focus:outline-none transition-default w-64";

const TOGGLE_BTN_BASE =
  "px-3 py-1.5 text-[13px] font-medium font-mono transition-default cursor-pointer";

export type PipelineView = "kanban" | "table";

export function PipelineToolbar({ view }: { view: PipelineView }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [nichos, setNichos] = useState<string[]>([]);
  const [cidades, setCidades] = useState<string[]>([]);

  // Snapshot current filter values from URL.
  const filters = useMemo(
    () => ({
      search: searchParams.get("search") ?? "",
      nicho: searchParams.get("nicho") ?? "",
      cidade: searchParams.get("cidade") ?? "",
      score_min: searchParams.get("score_min") ?? "",
      score_max: searchParams.get("score_max") ?? "",
      has_telefone: searchParams.get("has_telefone") ?? "",
      has_email: searchParams.get("has_email") ?? "",
      perfil_lead: (searchParams.get("perfil_lead") ?? "") as LeadProfile | "",
      nicho_canonico: (searchParams.get("nicho_canonico") ?? "") as NichoCanonico | "",
      order_by: searchParams.get("order_by") ?? "score_desc",
    }),
    [searchParams],
  );

  useEffect(() => {
    let cancelled = false;
    getLeadFilters()
      .then((data) => {
        if (cancelled) return;
        setNichos(data.nichos);
        setCidades(data.cidades);
      })
      .catch(() => {
        // best-effort; toolbar still works without dropdown options
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setQuery = useCallback(
    (key: string, value: string | null) => {
      const sp = new URLSearchParams(searchParams.toString());
      if (value && value.trim() !== "") {
        sp.set(key, value);
      } else {
        sp.delete(key);
      }
      router.replace(`?${sp.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const handleViewChange = useCallback(
    (next: PipelineView) => {
      try {
        localStorage.setItem("sdr-pipeline-view", next);
      } catch {
        // ignore
      }
      track("pipeline_view_toggled", { from: view, to: next });
      const sp = new URLSearchParams(searchParams.toString());
      sp.set("view", next);
      router.replace(`?${sp.toString()}`, { scroll: false });
    },
    [router, searchParams, view],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="t-eyebrow">Filtros</span>
        <input
          type="text"
          placeholder="Buscar por nome ou telefone..."
          value={filters.search}
          onChange={(e) => setQuery("search", e.target.value)}
          className={SEARCH_CLASS}
        />
        <select
          value={filters.nicho}
          onChange={(e) => setQuery("nicho", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Todos nichos</option>
          {nichos.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <select
          value={filters.cidade}
          onChange={(e) => setQuery("cidade", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Todas cidades</option>
          {cidades.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Score min"
          value={filters.score_min}
          onChange={(e) => setQuery("score_min", e.target.value)}
          className={INPUT_CLASS}
        />
        <input
          type="number"
          placeholder="Score máx"
          value={filters.score_max}
          onChange={(e) => setQuery("score_max", e.target.value)}
          className={INPUT_CLASS}
        />
        <select
          value={filters.has_telefone}
          onChange={(e) => setQuery("has_telefone", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Telefone: qualquer</option>
          <option value="true">Com telefone</option>
          <option value="false">Sem telefone</option>
        </select>
        <select
          value={filters.has_email}
          onChange={(e) => setQuery("has_email", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Email: qualquer</option>
          <option value="true">Com email</option>
          <option value="false">Sem email</option>
        </select>
        <select
          value={filters.perfil_lead}
          onChange={(e) => setQuery("perfil_lead", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Todos os perfis</option>
          {(Object.entries(LEAD_PROFILE_LABEL) as [LeadProfile, string][]).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={filters.nicho_canonico}
          onChange={(e) => setQuery("nicho_canonico", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="">Todos os nichos</option>
          {(Object.entries(NICHO_LABEL) as [NichoCanonico, string][]).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={filters.order_by}
          onChange={(e) => setQuery("order_by", e.target.value)}
          className={SELECT_CLASS}
        >
          <option value="score_desc">Maior score</option>
          <option value="score_asc">Menor score</option>
          <option value="prioridade">Prioridade</option>
          <option value="created_desc">Mais recente</option>
          <option value="updated_desc">Atualizado recente</option>
          <option value="name_asc">Nome A-Z</option>
        </select>

        <div className="ml-auto inline-flex rounded-md border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => handleViewChange("kanban")}
            className={`${TOGGLE_BTN_BASE} ${
              view === "kanban"
                ? "bg-accent-subtle text-accent"
                : "bg-surface-raised text-text-secondary hover:text-text"
            }`}
          >
            Kanban
          </button>
          <button
            type="button"
            onClick={() => handleViewChange("table")}
            className={`${TOGGLE_BTN_BASE} border-l border-border ${
              view === "table"
                ? "bg-accent-subtle text-accent"
                : "bg-surface-raised text-text-secondary hover:text-text"
            }`}
          >
            Tabela
          </button>
        </div>
      </div>
    </div>
  );
}
