"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";

import { getLeads } from "@/lib/api";
import { LEAD_PROFILE_LABEL, NICHO_LABEL, type Lead } from "@/lib/types";
import { Badge, Icon, StatusPill } from "@/components/ui";
import { buildWaLink } from "@/lib/format";
import { deriveSignals } from "@/lib/pipeline-signals";
import { ColumnVisibilityMenu } from "./column-visibility-menu";
import type { PipelineDensity } from "./use-pipeline-density";
import type { useBulkSelection } from "./use-bulk-selection";

const PER_PAGE = 50;
const ROW_HEIGHT = 48;
const COLUMN_VISIBILITY_STORAGE_KEY = "sdr-table-columns";

const DEFAULT_COLUMN_VISIBILITY: VisibilityState = {
  select: true,
  nome: true,
  nicho: true,
  cidade: true,
  opportunity_score: true,
  signals: true,
  contato: true,
  status: true,
  updated_at: true,
  actions: true,
  // optional defaults to false
  perfil_lead: false,
  telefone: false,
  email: false,
  cnpj: false,
  razao_social: false,
  tech_stack: false,
  reviews: false,
  pacote_sugerido: false,
  prioridade: false,
  created_at: false,
};

const MOBILE_COLUMN_VISIBILITY: VisibilityState = {
  select: true,
  nome: true,
  nicho: false,
  cidade: false,
  opportunity_score: true,
  signals: false,
  contato: true,
  status: true,
  updated_at: false,
  actions: true,
  perfil_lead: false,
  telefone: false,
  email: false,
  cnpj: false,
  razao_social: false,
  tech_stack: false,
  reviews: false,
  pacote_sugerido: false,
  prioridade: false,
  created_at: false,
};

const COLUMN_DESCRIPTORS: Array<{ id: string; label: string }> = [
  { id: "nome", label: "Nome" },
  { id: "nicho", label: "Nicho" },
  { id: "cidade", label: "Cidade" },
  { id: "opportunity_score", label: "Score" },
  { id: "signals", label: "Sinais" },
  { id: "contato", label: "Contato" },
  { id: "status", label: "Status" },
  { id: "updated_at", label: "Atualizado" },
  { id: "perfil_lead", label: "Perfil" },
  { id: "telefone", label: "Telefone" },
  { id: "email", label: "Email" },
  { id: "cnpj", label: "CNPJ" },
  { id: "razao_social", label: "Razão social" },
  { id: "tech_stack", label: "Tech stack" },
  { id: "reviews", label: "Reviews" },
  { id: "pacote_sugerido", label: "Pacote" },
  { id: "prioridade", label: "Prioridade" },
  { id: "created_at", label: "Criado" },
];

function loadVisibility(isMobile: boolean): VisibilityState {
  if (typeof window === "undefined") {
    return isMobile ? MOBILE_COLUMN_VISIBILITY : DEFAULT_COLUMN_VISIBILITY;
  }
  try {
    const raw = window.localStorage.getItem(COLUMN_VISIBILITY_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as VisibilityState;
      return { ...DEFAULT_COLUMN_VISIBILITY, ...parsed };
    }
  } catch {
    // ignore parse errors
  }
  return isMobile ? MOBILE_COLUMN_VISIBILITY : DEFAULT_COLUMN_VISIBILITY;
}

// ----- helpers -----

function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "—";
  const diffMs = Date.now() - ts;
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));
  if (diffSec < 60) return "agora";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `há ${diffMin}min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `há ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `há ${diffD}d`;
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

function scoreBucket(score: number): "high" | "mid" | "low" {
  if (score >= 80) return "high";
  if (score >= 50) return "mid";
  return "low";
}

// Backend sort vocabulary: score_desc | score_asc | name_asc | updated_desc (no asc)
type OrderBy =
  | "score_desc"
  | "score_asc"
  | "name_asc"
  | "updated_desc"
  | "created_desc"
  | "prioridade";

const KNOWN_ORDER_BY: Set<string> = new Set([
  "score_desc",
  "score_asc",
  "name_asc",
  "updated_desc",
  "created_desc",
  "prioridade",
]);

function sortingToOrderBy(sorting: SortingState): OrderBy | null {
  if (sorting.length === 0) return null;
  const [first] = sorting;
  if (first.id === "opportunity_score") {
    return first.desc ? "score_desc" : "score_asc";
  }
  if (first.id === "nome") {
    return "name_asc";
  }
  if (first.id === "updated_at") {
    return "updated_desc";
  }
  return null;
}

function orderByToSorting(orderBy: string | null): SortingState {
  switch (orderBy) {
    case "score_desc":
      return [{ id: "opportunity_score", desc: true }];
    case "score_asc":
      return [{ id: "opportunity_score", desc: false }];
    case "name_asc":
      return [{ id: "nome", desc: false }];
    case "updated_desc":
      return [{ id: "updated_at", desc: true }];
    default:
      return [];
  }
}

// Cycle through directions allowed by backend per column.
function cycleSort(columnId: string, current: SortingState): SortingState {
  const active = current.find((s) => s.id === columnId);
  if (columnId === "opportunity_score") {
    // none -> desc -> asc -> none
    if (!active) return [{ id: columnId, desc: true }];
    if (active.desc) return [{ id: columnId, desc: false }];
    return [];
  }
  if (columnId === "nome") {
    // backend supports asc only: none -> asc -> none
    if (!active) return [{ id: columnId, desc: false }];
    return [];
  }
  if (columnId === "updated_at") {
    // backend supports desc only: none -> desc -> none
    if (!active) return [{ id: columnId, desc: true }];
    return [];
  }
  return current;
}

function ariaSortFor(columnId: string, sorting: SortingState): "ascending" | "descending" | "none" {
  const active = sorting.find((s) => s.id === columnId);
  if (!active) return "none";
  return active.desc ? "descending" : "ascending";
}

// ----- component -----

interface PipelineTableProps {
  sel: ReturnType<typeof useBulkSelection>;
  density: PipelineDensity;
  onVisibleIdsChange?: (ids: number[]) => void;
  onTotalChange?: (total: number) => void;
  refreshKey?: number;
}

export function PipelineTable({
  sel,
  density,
  onVisibleIdsChange,
  onTotalChange,
  refreshKey,
}: PipelineTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Filters from URL
  const filters = useMemo(() => {
    const params: Record<string, string> = {};
    const keys = [
      "status",
      "nicho",
      "cidade",
      "score_min",
      "score_max",
      "has_telefone",
      "has_email",
      "search",
      "perfil_lead",
      "nicho_canonico",
    ];
    for (const k of keys) {
      const v = searchParams.get(k);
      if (v && v.trim() !== "") params[k] = v;
    }
    return params;
  }, [searchParams]);

  const orderByParam = searchParams.get("order_by");
  const pageParam = searchParams.get("page");

  // Derive sorting + page from URL (single source of truth).
  const sorting = useMemo<SortingState>(
    () => orderByToSorting(KNOWN_ORDER_BY.has(orderByParam ?? "") ? orderByParam : null),
    [orderByParam],
  );
  const page = useMemo(() => {
    const n = Number(pageParam ?? 1);
    return Number.isFinite(n) && n >= 1 ? Math.floor(n) : 1;
  }, [pageParam]);

  const [data, setData] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Column visibility — persisted to localStorage.
  // Detect mobile synchronously in the lazy initializer so the right default
  // is picked on first render. If we deferred mobile detection to an effect,
  // the persist effect below would write desktop defaults to localStorage
  // before the mobile effect ran — locking first-time mobile users into
  // desktop columns forever.
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
    () => {
      const isMobileAtMount =
        typeof window !== "undefined" &&
        window.matchMedia("(max-width: 768px)").matches;
      return loadVisibility(isMobileAtMount);
    },
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        COLUMN_VISIBILITY_STORAGE_KEY,
        JSON.stringify(columnVisibility),
      );
    } catch {
      // ignore quota / private mode errors
    }
  }, [columnVisibility]);

  // Bulk selection (sel passed from parent)
  const visibleIds = useMemo(() => data.map((l) => l.id), [data]);

  // Bubble visible ids and total up to parent so it can wire banner / action bar.
  useEffect(() => {
    onVisibleIdsChange?.(visibleIds);
  }, [visibleIds, onVisibleIdsChange]);

  useEffect(() => {
    onTotalChange?.(total);
  }, [total, onTotalChange]);
  const headerCheckState: "checked" | "indeterminate" | "unchecked" = useMemo(() => {
    if (visibleIds.length === 0) return "unchecked";
    const allSelected = visibleIds.every((id) => sel.has(id));
    if (allSelected) return "checked";
    const someSelected = visibleIds.some((id) => sel.has(id));
    return someSelected ? "indeterminate" : "unchecked";
  }, [visibleIds, sel]);

  // Build URL helper
  const updateUrl = useCallback(
    (mut: (sp: URLSearchParams) => void) => {
      const sp = new URLSearchParams(searchParams.toString());
      mut(sp);
      router.replace(`?${sp.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  // Fetch on filters/sort/page change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params: Record<string, string> = {
      ...filters,
      page: String(page),
      per_page: String(PER_PAGE),
    };
    const ob = sortingToOrderBy(sorting);
    if (ob) params.order_by = ob;
    else if (orderByParam && KNOWN_ORDER_BY.has(orderByParam)) {
      // Preserve toolbar-chosen order (e.g. "prioridade", "created_desc") when no
      // table header is sorting.
      params.order_by = orderByParam;
    }

    getLeads(params)
      .then((res) => {
        if (cancelled) return;
        setData(res.items);
        setTotal(res.total);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Erro ao carregar leads");
        setData([]);
        setTotal(0);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, sorting, page, orderByParam, refreshKey]);

  // Keyboard shortcuts: Cmd/Ctrl+A selects current page, Esc clears selection
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "a") {
        const inTable =
          document.activeElement?.closest("table") !== null ||
          document.activeElement === document.body;
        if (inTable && visibleIds.length > 0) {
          e.preventDefault();
          sel.togglePage(visibleIds);
        }
      }
      if (e.key === "Escape" && sel.size > 0) {
        sel.clear();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [visibleIds, sel]);

  // Header click -> push order_by + reset page
  const handleSort = useCallback(
    (columnId: string) => {
      const next = cycleSort(columnId, sorting);
      const nextOrder = sortingToOrderBy(next);
      updateUrl((sp) => {
        if (nextOrder) sp.set("order_by", nextOrder);
        else sp.delete("order_by");
        sp.delete("page");
      });
    },
    [sorting, updateUrl],
  );

  const handlePage = useCallback(
    (next: number) => {
      updateUrl((sp) => {
        if (next <= 1) sp.delete("page");
        else sp.set("page", String(next));
      });
    },
    [updateUrl],
  );

  // Columns
  const columns = useMemo<ColumnDef<Lead>[]>(
    () => [
      {
        id: "select",
        size: 40,
        header: () => (
          <div className="flex h-full min-h-[40px] w-full items-center justify-center px-2">
            <button
              type="button"
              role="checkbox"
              aria-checked={
                headerCheckState === "indeterminate"
                  ? "mixed"
                  : headerCheckState === "checked"
              }
              aria-label="Selecionar página"
              onClick={() => sel.togglePage(visibleIds)}
              className={`flex h-4 w-4 items-center justify-center rounded border transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 ${
                headerCheckState === "checked"
                  ? "border-accent bg-accent text-surface"
                  : "border-border bg-surface-raised hover:border-border-strong"
              }`}
            >
              {headerCheckState === "checked" && (
                <Icon name="check" size={12} />
              )}
              {headerCheckState === "indeterminate" && (
                <span className="block h-0.5 w-2 bg-accent" />
              )}
            </button>
          </div>
        ),
        cell: ({ row }) => {
          const lead = row.original;
          const checked = sel.has(lead.id);
          return (
            <div
              className="flex h-full min-h-[40px] w-full items-center justify-center px-2"
              data-cell="select"
              onClick={(e) => {
                // Wider touch hit area: clicking anywhere in the cell toggles
                // the checkbox without navigating into the row.
                e.stopPropagation();
                if (e.target === e.currentTarget) {
                  sel.toggle(lead.id);
                }
              }}
            >
              <button
                type="button"
                role="checkbox"
                aria-checked={checked}
                aria-label={`Selecionar lead ${lead.nome}`}
                onClick={(e) => {
                  e.stopPropagation();
                  if (e.shiftKey && sel.lastClickedId !== null) {
                    sel.selectRange(sel.lastClickedId, lead.id, visibleIds);
                  } else {
                    sel.toggle(lead.id);
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === " " || e.key === "Enter") {
                    e.preventDefault();
                    e.stopPropagation();
                    sel.toggle(lead.id);
                  }
                }}
                className={`flex h-4 w-4 items-center justify-center rounded border transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 ${
                  checked
                    ? "border-accent bg-accent text-surface"
                    : "border-border bg-surface-raised hover:border-border-strong"
                }`}
              >
                {checked && <Icon name="check" size={12} />}
              </button>
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "nome",
        accessorKey: "nome",
        header: () => <span>Nome</span>,
        cell: ({ row }) => {
          const lead = row.original;
          return (
            <div className="pl-tbl-name">
              <div className="pl-tbl-name-strong">{lead.nome}</div>
              <div className="pl-tbl-name-sub">
                {lead.rating != null && (
                  <span className="pl-tbl-rating">
                    <span className="pl-card-meta-star">★</span>
                    <span>{lead.rating.toFixed(1).replace(".", ",")}</span>
                  </span>
                )}
                {lead.reviews_count > 0 && (
                  <span className="pl-tbl-reviews">· {lead.reviews_count} reviews</span>
                )}
              </div>
            </div>
          );
        },
        enableSorting: true,
      },
      {
        id: "nicho",
        size: 160,
        header: () => <span>Nicho</span>,
        cell: ({ row }) => {
          const lead = row.original;
          const label =
            lead.nicho_canonico && NICHO_LABEL[lead.nicho_canonico]
              ? NICHO_LABEL[lead.nicho_canonico]
              : lead.nicho ?? "—";
          if (label === "—") {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          return <span className="pl-tbl-niche-chip">{label}</span>;
        },
        enableSorting: false,
      },
      {
        id: "cidade",
        accessorKey: "cidade",
        size: 140,
        header: () => <span>Cidade</span>,
        cell: ({ row }) => (
          <span className="pl-tbl-city">{row.original.cidade ?? "—"}</span>
        ),
        enableSorting: false,
      },
      {
        id: "opportunity_score",
        accessorKey: "opportunity_score",
        size: 110,
        header: () => <span>Score</span>,
        cell: ({ row }) => {
          const s = row.original.opportunity_score;
          if (s == null) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          const bucket = scoreBucket(s);
          return (
            <div className={`pl-tbl-score-cell pl-tbl-score-${bucket}`}>
              <span className="pl-tbl-score-num">{s}</span>
              <span className="pl-tbl-score-bar" aria-hidden="true">
                <span style={{ width: `${s}%` }} />
              </span>
            </div>
          );
        },
        enableSorting: true,
      },
      {
        id: "signals",
        size: 220,
        header: () => <span>Sinais</span>,
        cell: ({ row }) => {
          const signals = deriveSignals(row.original.opportunity_reasons).slice(0, 3);
          if (signals.length === 0) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          return (
            <div className="pl-tbl-signals-list">
              {signals.map((s) => (
                <span key={s.key} className={`pl-signal pl-signal-${s.tone}`}>
                  {s.tone === "danger" && <span className="pl-signal-dot" />}
                  {s.label}
                </span>
              ))}
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "contato",
        size: 100,
        header: () => <span>Contato</span>,
        cell: ({ row }) => {
          const lead = row.original;
          return (
            <div className="pl-tbl-contact-icons">
              <span
                className={lead.telefone ? "ok" : "off"}
                title={lead.telefone || "sem telefone"}
              >
                <Icon name="phone" size={13} />
              </span>
              <span
                className={lead.email ? "ok" : "off"}
                title={lead.email || "sem email"}
              >
                <Icon name="mail" size={13} />
              </span>
              <span className="off" title="WhatsApp não validado">
                <Icon name="wa" size={13} />
              </span>
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "perfil_lead",
        size: 140,
        header: () => <span>Perfil</span>,
        cell: ({ row }) => {
          const p = row.original.perfil_lead;
          if (!p) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          const label = LEAD_PROFILE_LABEL[p];
          const variant: "danger" | "warn" | "default" | "ok" =
            p === "hot_no_site" || p === "hot_bad_site"
              ? "danger"
              : p === "warm"
                ? "warn"
                : p === "cold"
                  ? "ok"
                  : "default";
          return (
            <div className="px-3">
              <Badge variant={variant}>{label}</Badge>
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "status",
        size: 140,
        header: () => <span>Status</span>,
        cell: ({ row }) => (
          <div className="px-3">
            <StatusPill status={row.original.status} />
          </div>
        ),
        enableSorting: false,
      },
      {
        id: "updated_at",
        size: 120,
        header: () => <span>Atualizado</span>,
        cell: ({ row }) => (
          <span className="pl-tbl-when">
            {formatRelativeTime(row.original.updated_at)}
          </span>
        ),
        enableSorting: true,
      },
      {
        id: "actions",
        size: 96,
        header: () => <span aria-label="Ações" />,
        cell: ({ row }) => {
          const lead = row.original;
          const waLink = buildWaLink(lead.telefone);
          return (
            <div
              className="pl-tbl-actions"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                className="pl-tbl-action"
                title="Enriquecer"
                aria-label={`Enriquecer ${lead.nome}`}
                onClick={() => router.push(`/app/leads/${lead.id}`)}
              >
                <Icon name="sparkle" size={13} />
              </button>
              <button
                type="button"
                className="pl-tbl-action"
                title={waLink ? "Abrir WhatsApp" : "Sem telefone"}
                aria-label="Abrir WhatsApp"
                disabled={!waLink}
                onClick={() => waLink && window.open(waLink, "_blank", "noopener,noreferrer")}
              >
                <Icon name="phone" size={13} />
              </button>
              <button
                type="button"
                className="pl-tbl-action"
                title="Mais"
                aria-label="Mais"
                onClick={() => router.push(`/app/leads/${lead.id}`)}
              >
                <Icon name="more" size={13} />
              </button>
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "telefone",
        accessorKey: "telefone",
        header: () => <span>Telefone</span>,
        size: 140,
        cell: ({ row }) => {
          const v = row.original.telefone;
          return v ? (
            <span className="font-mono tabular-nums text-[13px] px-3 truncate block">
              {v}
            </span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "email",
        accessorKey: "email",
        header: () => <span>Email</span>,
        size: 200,
        cell: ({ row }) => {
          const v = row.original.email;
          return v ? (
            <span className="text-[13px] px-3 truncate block">{v}</span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "cnpj",
        accessorKey: "cnpj",
        header: () => <span>CNPJ</span>,
        size: 160,
        cell: ({ row }) => {
          const v = row.original.cnpj;
          return v ? (
            <span className="font-mono tabular-nums text-[12px] px-3 truncate block">
              {v}
            </span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "razao_social",
        accessorKey: "razao_social",
        header: () => <span>Razão social</span>,
        size: 200,
        cell: ({ row }) => {
          const v = row.original.razao_social;
          return v ? (
            <span className="text-[13px] px-3 truncate block">{v}</span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "tech_stack",
        accessorKey: "tech_stack",
        header: () => <span>Tech</span>,
        size: 180,
        cell: ({ row }) => {
          const v = row.original.tech_stack ?? [];
          if (v.length === 0) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          return (
            <div className="flex flex-wrap gap-1 px-3">
              {v.slice(0, 3).map((t, i) => (
                <span
                  key={i}
                  className="t-eyebrow rounded bg-surface-raised px-1.5 py-0.5"
                >
                  {t.name}
                </span>
              ))}
              {v.length > 3 && (
                <span className="t-eyebrow text-text-muted">
                  +{v.length - 3}
                </span>
              )}
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "reviews",
        header: () => <span>Reviews</span>,
        size: 110,
        cell: ({ row }) => {
          const rating = row.original.rating;
          const count = row.original.reviews_count ?? 0;
          if (rating == null) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          return (
            <span className="font-mono tabular-nums text-[12px] px-3">
              {rating.toFixed(1)}{" "}
              <span className="text-text-muted">({count})</span>
            </span>
          );
        },
        enableSorting: false,
      },
      {
        id: "pacote_sugerido",
        accessorKey: "pacote_sugerido",
        header: () => <span>Pacote</span>,
        size: 120,
        cell: ({ row }) => {
          const v = row.original.pacote_sugerido;
          return v ? (
            <span className="t-eyebrow uppercase px-3">{v}</span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "prioridade",
        accessorKey: "prioridade",
        header: () => <span>Prioridade</span>,
        size: 120,
        cell: ({ row }) => {
          const v = row.original.prioridade;
          return v ? (
            <span className="t-eyebrow uppercase px-3">{v}</span>
          ) : (
            <span className="text-text-muted text-[13px] px-3">—</span>
          );
        },
        enableSorting: false,
      },
      {
        id: "created_at",
        accessorKey: "created_at",
        header: () => <span>Criado</span>,
        size: 120,
        cell: ({ row }) => (
          <span className="text-text-muted text-[12px] font-mono tabular-nums px-3">
            {formatRelativeTime(row.original.created_at)}
          </span>
        ),
        enableSorting: false,
      },
    ],
    [sel, visibleIds, headerCheckState, router],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    manualSorting: true,
    manualPagination: true,
    pageCount: Math.max(1, Math.ceil(total / PER_PAGE)),
    getCoreRowModel: getCoreRowModel(),
  });

  // Virtualization
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const rows = table.getRowModel().rows;
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const isFirst = page <= 1;
  const isLast = page >= totalPages;

  const navigateToLead = useCallback(
    (leadId: number) => {
      router.push(`/app/leads/${leadId}`);
    },
    [router],
  );

  // Row click -> /app/leads/[id], unless click started in checkbox cell.
  const handleRowClick = useCallback(
    (e: React.MouseEvent, leadId: number) => {
      const target = e.target as HTMLElement;
      if (target.closest('[data-cell="select"]')) return;
      navigateToLead(leadId);
    },
    [navigateToLead],
  );

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <ColumnVisibilityMenu
          columns={COLUMN_DESCRIPTORS}
          visibility={columnVisibility as Record<string, boolean>}
          onChange={setColumnVisibility}
        />
      </div>
      <div
        className={`pl-tbl-wrap${density === "compact" ? " pl-tbl-compact" : ""}`}
      >
        <div
          ref={scrollRef}
          className="overflow-auto"
          style={{ maxHeight: "calc(100vh - 320px)" }}
        >
          <table className="pl-tbl">
            <thead className="sticky top-0 z-10">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const canSort = header.column.getCanSort();
                    const sortDir = ariaSortFor(header.column.id, sorting);
                    const sortIcon =
                      sortDir === "ascending"
                        ? "arrow-u"
                        : sortDir === "descending"
                          ? "arrow-d"
                          : null;
                    const size = header.column.columnDef.size;
                    const styleProp =
                      typeof size === "number" && header.column.id !== "nome"
                        ? { width: size, minWidth: size }
                        : undefined;
                    return (
                      <th
                        key={header.id}
                        scope="col"
                        aria-sort={canSort ? sortDir : undefined}
                        style={styleProp}
                      >
                        {canSort ? (
                          <button
                            type="button"
                            onClick={() => handleSort(header.column.id)}
                            className="pl-tbl-sort"
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                            {sortIcon ? (
                              <Icon name={sortIcon} size={11} />
                            ) : (
                              <span style={{ opacity: 0.35 }}>
                                <Icon name="sort" size={11} />
                              </span>
                            )}
                          </button>
                        ) : (
                          flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>

            {loading ? (
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr
                    key={`sk-${i}`}
                    className="border-b border-border/60 animate-pulse"
                    style={{ height: ROW_HEIGHT }}
                  >
                    {table.getAllColumns().map((col) => (
                      <td key={col.id} className="px-3">
                        <div className="h-3 w-3/4 rounded-xs bg-paper-2/60" />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            ) : error ? (
              <tbody>
                <tr>
                  <td
                    colSpan={table.getAllColumns().length}
                    className="p-6 text-center"
                  >
                    <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-danger/40 bg-danger-soft text-danger text-[13px]">
                      <Icon name="error" size={14} />
                      <span>{error}</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            ) : total === 0 ? (
              <tbody>
                <tr>
                  <td
                    colSpan={table.getAllColumns().length}
                    className="p-10 text-center text-text-muted text-sm"
                  >
                    Nenhum lead encontrado. Tente ajustar filtros.
                  </td>
                </tr>
              </tbody>
            ) : (
              <tbody
                style={{
                  display: "block",
                  height: rowVirtualizer.getTotalSize(),
                  position: "relative",
                  width: "100%",
                }}
              >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const row = rows[virtualRow.index];
                  if (!row) return null;
                  const lead = row.original;
                  const isHot = (lead.opportunity_score ?? 0) >= 80;
                  const isSelected = sel.has(lead.id);
                  const rowClass = [
                    "cursor-pointer",
                    isSelected ? "pl-tbl-row-selected" : "",
                    isHot && !isSelected ? "pl-tbl-row-hot" : "",
                  ]
                    .filter(Boolean)
                    .join(" ");
                  return (
                    <tr
                      key={row.id}
                      onClick={(e) => handleRowClick(e, lead.id)}
                      onKeyDown={(e) => {
                        if (
                          (e.key === "Enter" || e.key === " ") &&
                          e.target === e.currentTarget
                        ) {
                          e.preventDefault();
                          navigateToLead(lead.id);
                        }
                      }}
                      className={rowClass}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: ROW_HEIGHT,
                        transform: `translateY(${virtualRow.start}px)`,
                        display: "table",
                        tableLayout: "fixed",
                      }}
                      tabIndex={0}
                    >
                      {row.getVisibleCells().map((cell) => {
                        const size = cell.column.columnDef.size;
                        const styleProp =
                          typeof size === "number" && cell.column.id !== "nome"
                            ? { width: size, minWidth: size }
                            : undefined;
                        return (
                          <td
                            key={cell.id}
                            style={styleProp}
                            className="align-middle"
                          >
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext(),
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            )}
          </table>
        </div>
        <div className="pl-tbl-foot">
          <div className="pl-tbl-foot-l">
            <span>Mostrando</span>
            <span className="pl-tbl-foot-strong">{data.length}</span>
            <span>de</span>
            <span className="pl-tbl-foot-strong">{total}</span>
            <span>leads</span>
            {totalPages > 1 && (
              <>
                <span className="pl-tbl-foot-sep">·</span>
                <span>
                  página{" "}
                  <span className="pl-tbl-foot-strong">{page}</span> de{" "}
                  <span className="pl-tbl-foot-strong">{totalPages}</span>
                </span>
              </>
            )}
          </div>
          <div className="pl-tbl-foot-r">
            <button
              type="button"
              disabled={isFirst || loading}
              onClick={() => handlePage(page - 1)}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-mono rounded-md border border-border-strong bg-surface text-text-strong hover:bg-surface-raised disabled:opacity-40 disabled:cursor-not-allowed transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 cursor-pointer"
            >
              <Icon name="chevron-r" size={11} className="rotate-180" />
              Anterior
            </button>
            <button
              type="button"
              disabled={isLast || loading}
              onClick={() => handlePage(page + 1)}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-mono rounded-md border border-border-strong bg-surface text-text-strong hover:bg-surface-raised disabled:opacity-40 disabled:cursor-not-allowed transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 cursor-pointer"
            >
              Próxima
              <Icon name="chevron-r" size={11} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
