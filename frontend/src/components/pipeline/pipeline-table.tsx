"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";

import { getLeads } from "@/lib/api";
import { LEAD_PROFILE_LABEL, NICHO_LABEL, type Lead } from "@/lib/types";
import { Badge, Icon, StatusPill, Tag } from "@/components/ui";
import type { useBulkSelection } from "./use-bulk-selection";

const PER_PAGE = 50;
const ROW_HEIGHT = 48;

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

function scoreClass(score: number): string {
  if (score >= 80) return "score-high";
  if (score >= 50) return "score-mid";
  return "score-low";
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
  onVisibleIdsChange?: (ids: number[]) => void;
  onTotalChange?: (total: number) => void;
  refreshKey?: number;
}

export function PipelineTable({
  sel,
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
          <div className="flex items-center justify-center px-2">
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
              className="flex items-center justify-center px-2"
              data-cell="select"
              onClick={(e) => e.stopPropagation()}
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
            <div className="flex flex-col min-w-0 px-3">
              <span className="text-text font-medium text-[13px] truncate">
                {lead.nome}
              </span>
              {lead.telefone ? (
                <span className="text-text-muted text-[11px] font-mono tabular-nums truncate">
                  {lead.telefone}
                </span>
              ) : null}
            </div>
          );
        },
        enableSorting: true,
      },
      {
        id: "cidade",
        accessorKey: "cidade",
        size: 140,
        header: () => <span>Cidade</span>,
        cell: ({ row }) => (
          <span className="text-text-secondary text-[13px] px-3 truncate block">
            {row.original.cidade ?? "—"}
          </span>
        ),
        enableSorting: false,
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
          return (
            <div className="px-3">
              <Tag>{label}</Tag>
            </div>
          );
        },
        enableSorting: false,
      },
      {
        id: "opportunity_score",
        accessorKey: "opportunity_score",
        size: 80,
        header: () => <span>Score</span>,
        cell: ({ row }) => {
          const s = row.original.opportunity_score;
          if (s == null) {
            return <span className="text-text-muted text-[13px] px-3">—</span>;
          }
          return (
            <span
              className={`font-mono tabular-nums text-[13px] font-medium px-3 ${scoreClass(s)}`}
            >
              {s}
            </span>
          );
        },
        enableSorting: true,
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
          <span className="text-text-muted text-[12px] font-mono tabular-nums px-3">
            {formatRelativeTime(row.original.updated_at)}
          </span>
        ),
        enableSorting: true,
      },
    ],
    [sel, visibleIds, headerCheckState],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
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

  // Row click -> /app/leads/[id], unless click started in checkbox cell.
  const handleRowClick = useCallback(
    (e: React.MouseEvent, leadId: number) => {
      const target = e.target as HTMLElement;
      if (target.closest('[data-cell="select"]')) return;
      router.push(`/app/leads/${leadId}`);
    },
    [router],
  );

  return (
    <div className="space-y-3">
      <div className="border border-border rounded-lg bg-surface overflow-hidden">
        <div
          ref={scrollRef}
          className="overflow-auto"
          style={{ maxHeight: "calc(100vh - 320px)" }}
        >
          <table className="w-full border-collapse text-left">
            <thead className="sticky top-0 z-10 bg-surface-raised border-b border-border">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const canSort = header.column.getCanSort();
                    const sortDir = ariaSortFor(header.column.id, sorting);
                    const sortIcon =
                      sortDir === "ascending"
                        ? "arrow-d"
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
                        className="t-eyebrow text-text-muted text-left h-9 align-middle whitespace-nowrap"
                      >
                        {canSort ? (
                          <button
                            type="button"
                            onClick={() => handleSort(header.column.id)}
                            className="inline-flex items-center gap-1 px-3 h-full w-full text-left hover:text-text transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 cursor-pointer"
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                            {sortIcon ? (
                              <span
                                className={`inline-flex transition-default ${
                                  sortDir === "descending" ? "" : "rotate-180"
                                }`}
                              >
                                <Icon name={sortIcon} size={12} />
                              </span>
                            ) : (
                              <span className="opacity-30">
                                <Icon name="sort" size={12} />
                              </span>
                            )}
                          </button>
                        ) : (
                          <div className="px-3 h-full flex items-center">
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                          </div>
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
                  return (
                    <tr
                      key={row.id}
                      onClick={(e) => handleRowClick(e, lead.id)}
                      className="border-b border-border/60 hover:bg-surface-raised cursor-pointer transition-default"
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
      </div>

      {/* Pagination footer */}
      <div className="flex items-center justify-between text-[13px]">
        <div className="text-text-muted font-mono tabular-nums">
          {total > 0
            ? `página ${page} de ${totalPages} · ${total} leads`
            : "—"}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isFirst || loading}
            onClick={() => handlePage(page - 1)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-[13px] font-medium font-mono rounded-md border border-border bg-surface-raised text-text-secondary hover:text-text hover:border-border-strong disabled:opacity-40 disabled:cursor-not-allowed transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 cursor-pointer"
          >
            <Icon name="chevron-r" size={12} className="rotate-180" />
            Prev
          </button>
          <button
            type="button"
            disabled={isLast || loading}
            onClick={() => handlePage(page + 1)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-[13px] font-medium font-mono rounded-md border border-border bg-surface-raised text-text-secondary hover:text-text hover:border-border-strong disabled:opacity-40 disabled:cursor-not-allowed transition-default focus:outline-none focus:ring-2 focus:ring-accent/50 cursor-pointer"
          >
            Next
            <Icon name="chevron-r" size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}
