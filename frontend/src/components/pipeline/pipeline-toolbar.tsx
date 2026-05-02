"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getLeadFilters } from "@/lib/api";
import { LEAD_PROFILE_LABEL, NICHO_LABEL } from "@/lib/types";
import type { LeadProfile, NichoCanonico } from "@/lib/types";
import { track } from "@/lib/telemetry";
import { Icon } from "@/components/ui";
import { usePipelineDensity } from "./use-pipeline-density";

export type PipelineView = "kanban" | "table";

const ADVANCED_KEYS = ["perfil_lead", "nicho_canonico", "has_telefone", "has_email"] as const;

const SORT_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "score_desc", label: "Maior score" },
  { value: "score_asc", label: "Menor score" },
  { value: "prioridade", label: "Prioridade" },
  { value: "created_desc", label: "Mais recente" },
  { value: "updated_desc", label: "Atualizado recente" },
  { value: "name_asc", label: "Nome A-Z" },
];

function shortLabel(value: string, fallback: string, maxLen = 22): string {
  if (!value) return fallback;
  return value.length > maxLen ? `${value.slice(0, maxLen - 1)}…` : value;
}

interface ChipMenuProps {
  active: boolean;
  label: string;
  count?: number;
  ariaLabel: string;
  children: (close: () => void) => React.ReactNode;
}

function ChipMenu({ active, label, count, ariaLabel, children }: ChipMenuProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        className={`pl-chip${active ? " pl-chip-active" : ""}`}
      >
        <span>{label}</span>
        {typeof count === "number" && count > 0 && (
          <span className="pl-chip-count">{count}</span>
        )}
        <Icon name="chevron-d" size={11} />
      </button>
      {open && (
        <div className="pl-chip-pop" role="listbox">
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

export function PipelineToolbar({ view }: { view: PipelineView }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [nichos, setNichos] = useState<string[]>([]);
  const [cidades, setCidades] = useState<string[]>([]);
  const { density, toggle: toggleDensity } = usePipelineDensity();

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

  const advancedOpen = searchParams.get("adv") === "1";
  const advancedActive = ADVANCED_KEYS.filter((k) => filters[k] !== "").length;

  useEffect(() => {
    let cancelled = false;
    getLeadFilters()
      .then((data) => {
        if (cancelled) return;
        setNichos(data.nichos);
        setCidades(data.cidades);
      })
      .catch(() => {
        // best-effort
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

  const setQueries = useCallback(
    (entries: Record<string, string | null>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(entries)) {
        if (v && v.trim() !== "") sp.set(k, v);
        else sp.delete(k);
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

  const toggleAdvanced = useCallback(() => {
    const sp = new URLSearchParams(searchParams.toString());
    if (advancedOpen) sp.delete("adv");
    else sp.set("adv", "1");
    router.replace(`?${sp.toString()}`, { scroll: false });
  }, [router, searchParams, advancedOpen]);

  // Apply density class on the page wrapper so it cascades to kanban + table.
  useEffect(() => {
    const root = document.querySelector(".pl-page");
    if (!root) return;
    root.classList.toggle("pl-density-compact", density === "compact");
    return () => {
      root.classList.remove("pl-density-compact");
    };
  }, [density]);

  return (
    <div className="pl-toolbar">
      <div className="pl-toolbar-search">
        <span className="pl-toolbar-search-icon" aria-hidden="true">
          <Icon name="search" size={14} />
        </span>
        <input
          type="text"
          placeholder="Buscar lead, telefone, cidade..."
          value={filters.search}
          onChange={(e) => setQuery("search", e.target.value)}
          aria-label="Buscar"
        />
        <span className="pl-toolbar-kbd">⌘K</span>
      </div>

      <div className="pl-toolbar-filters">
        <ChipMenu
          active={!!filters.nicho}
          label={shortLabel(filters.nicho, "Todos nichos")}
          ariaLabel="Filtrar por nicho"
        >
          {(close) => (
            <>
              <button
                type="button"
                className={`pl-chip-pop-item${!filters.nicho ? " selected" : ""}`}
                onClick={() => {
                  setQuery("nicho", "");
                  close();
                }}
              >
                Todos nichos
              </button>
              {nichos.length === 0 ? (
                <div className="pl-chip-pop-empty">Nenhum nicho disponível</div>
              ) : (
                nichos.map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`pl-chip-pop-item${filters.nicho === n ? " selected" : ""}`}
                    onClick={() => {
                      setQuery("nicho", n);
                      close();
                    }}
                  >
                    {n}
                  </button>
                ))
              )}
            </>
          )}
        </ChipMenu>

        <ChipMenu
          active={!!filters.cidade}
          label={shortLabel(filters.cidade, "Todas cidades")}
          ariaLabel="Filtrar por cidade"
        >
          {(close) => (
            <>
              <button
                type="button"
                className={`pl-chip-pop-item${!filters.cidade ? " selected" : ""}`}
                onClick={() => {
                  setQuery("cidade", "");
                  close();
                }}
              >
                Todas cidades
              </button>
              {cidades.length === 0 ? (
                <div className="pl-chip-pop-empty">Nenhuma cidade disponível</div>
              ) : (
                cidades.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`pl-chip-pop-item${filters.cidade === c ? " selected" : ""}`}
                    onClick={() => {
                      setQuery("cidade", c);
                      close();
                    }}
                  >
                    {c}
                  </button>
                ))
              )}
            </>
          )}
        </ChipMenu>

        <ChipMenu
          active={!!(filters.score_min || filters.score_max)}
          label={
            filters.score_min || filters.score_max
              ? `Score: ${filters.score_min || "0"}–${filters.score_max || "100"}`
              : "Score: ≥0"
          }
          ariaLabel="Filtrar por score"
        >
          {() => (
            <>
              <div className="pl-chip-pop-row">
                <label htmlFor="score-min">Min</label>
                <input
                  id="score-min"
                  type="number"
                  min={0}
                  max={100}
                  placeholder="0"
                  value={filters.score_min}
                  onChange={(e) => setQuery("score_min", e.target.value)}
                />
              </div>
              <div className="pl-chip-pop-row">
                <label htmlFor="score-max">Max</label>
                <input
                  id="score-max"
                  type="number"
                  min={0}
                  max={100}
                  placeholder="100"
                  value={filters.score_max}
                  onChange={(e) => setQuery("score_max", e.target.value)}
                />
              </div>
              {(filters.score_min || filters.score_max) && (
                <button
                  type="button"
                  className="pl-chip-pop-item"
                  onClick={() => setQueries({ score_min: null, score_max: null })}
                >
                  Limpar
                </button>
              )}
            </>
          )}
        </ChipMenu>

        <button
          type="button"
          onClick={toggleAdvanced}
          aria-pressed={advancedOpen}
          aria-controls="pl-toolbar-more"
          className={`pl-chip${advancedOpen || advancedActive > 0 ? " pl-chip-active" : ""}`}
        >
          <span>Mais filtros</span>
          {advancedActive > 0 && <span className="pl-chip-count">{advancedActive}</span>}
          <Icon name={advancedOpen ? "chevron-d" : "chevron-r"} size={11} />
        </button>
      </div>

      <div className="pl-toolbar-spacer" />

      <select
        value={filters.order_by}
        onChange={(e) => setQuery("order_by", e.target.value)}
        className="pl-toolbar-sort"
        aria-label="Ordenar por"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <div className="pl-view-toggle" role="tablist" aria-label="Visualização">
        <button
          type="button"
          role="tab"
          aria-selected={view === "kanban"}
          onClick={() => handleViewChange("kanban")}
          className={`pl-view-btn${view === "kanban" ? " active" : ""}`}
        >
          <Icon name="board" size={12} /> Kanban
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === "table"}
          onClick={() => handleViewChange("table")}
          className={`pl-view-btn${view === "table" ? " active" : ""}`}
        >
          <Icon name="list" size={12} /> Tabela
        </button>
      </div>

      {view === "table" && (
        <button
          type="button"
          onClick={toggleDensity}
          aria-label={density === "compact" ? "Aumentar densidade (confortável)" : "Reduzir densidade (compacto)"}
          title={density === "compact" ? "Atual: compacto" : "Atual: confortável"}
          className={`pl-density-btn${density === "compact" ? " active" : ""}`}
        >
          <Icon name={density === "compact" ? "list" : "doc"} size={13} />
        </button>
      )}

      {advancedOpen && (
        <div className="pl-toolbar-more" id="pl-toolbar-more">
          <select
            value={filters.perfil_lead}
            onChange={(e) => setQuery("perfil_lead", e.target.value)}
            className="pl-chip"
            aria-label="Filtrar por perfil"
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
            className="pl-chip"
            aria-label="Filtrar por nicho canônico"
          >
            <option value="">Todos nichos canônicos</option>
            {(Object.entries(NICHO_LABEL) as [NichoCanonico, string][]).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
          <select
            value={filters.has_telefone}
            onChange={(e) => setQuery("has_telefone", e.target.value)}
            className="pl-chip"
            aria-label="Filtrar por telefone"
          >
            <option value="">Telefone: qualquer</option>
            <option value="true">Com telefone</option>
            <option value="false">Sem telefone</option>
          </select>
          <select
            value={filters.has_email}
            onChange={(e) => setQuery("has_email", e.target.value)}
            className="pl-chip"
            aria-label="Filtrar por email"
          >
            <option value="">Email: qualquer</option>
            <option value="true">Com email</option>
            <option value="false">Sem email</option>
          </select>
        </div>
      )}
    </div>
  );
}
