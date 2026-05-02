"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getLeadIds } from "@/lib/api";

const STORAGE_KEY = "sdr-bulk-selection";
const MAX_BULK_IDS = 5000;

export type SelectionMode = "ids" | "all_filter";

interface SelectionState {
  mode: SelectionMode;
  ids: Set<number>;
  excludedIds: Set<number>;
  filterSnapshot: Record<string, string>;
  totalInFilter: number;
  lastClickedId: number | null;
}

export interface BulkSelection {
  mode: SelectionMode;
  size: number;
  has: (id: number) => boolean;
  toggle: (id: number) => void;
  selectRange: (fromId: number, toId: number, visibleIds: number[]) => void;
  togglePage: (visibleIds: number[]) => void;
  selectAllFilter: (filters: Record<string, string>, total: number) => void;
  clear: () => void;
  materializeIds: () => Promise<number[]>;
  isAllFilterMode: boolean;
  filterSnapshot: Record<string, string>;
  totalInFilter: number;
  lastClickedId: number | null;
}

const initialState: SelectionState = {
  mode: "ids",
  ids: new Set<number>(),
  excludedIds: new Set<number>(),
  filterSnapshot: {},
  totalInFilter: 0,
  lastClickedId: null,
};

function loadState(): SelectionState {
  if (typeof window === "undefined") return initialState;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const parsed = JSON.parse(raw);
    return {
      mode: parsed.mode === "all_filter" ? "all_filter" : "ids",
      ids: new Set<number>(
        Array.isArray(parsed.ids)
          ? parsed.ids.filter((x: unknown): x is number => typeof x === "number")
          : [],
      ),
      excludedIds: new Set<number>(
        Array.isArray(parsed.excludedIds)
          ? parsed.excludedIds.filter((x: unknown): x is number => typeof x === "number")
          : [],
      ),
      filterSnapshot:
        parsed.filterSnapshot && typeof parsed.filterSnapshot === "object"
          ? (parsed.filterSnapshot as Record<string, string>)
          : {},
      totalInFilter: typeof parsed.totalInFilter === "number" ? parsed.totalInFilter : 0,
      lastClickedId: typeof parsed.lastClickedId === "number" ? parsed.lastClickedId : null,
    };
  } catch {
    return initialState;
  }
}

function saveState(state: SelectionState) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        mode: state.mode,
        ids: [...state.ids],
        excludedIds: [...state.excludedIds],
        filterSnapshot: state.filterSnapshot,
        totalInFilter: state.totalInFilter,
        lastClickedId: state.lastClickedId,
      }),
    );
  } catch {
    // sessionStorage unavailable; ignore
  }
}

export function useBulkSelection(): BulkSelection {
  const [state, setState] = useState<SelectionState>(loadState);

  useEffect(() => {
    saveState(state);
  }, [state]);

  const toggle = useCallback((id: number) => {
    setState((prev) => {
      if (prev.mode === "ids") {
        const next = new Set(prev.ids);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return { ...prev, ids: next, lastClickedId: id };
      }
      const nextExcluded = new Set(prev.excludedIds);
      if (nextExcluded.has(id)) {
        nextExcluded.delete(id);
      } else {
        nextExcluded.add(id);
      }
      return { ...prev, excludedIds: nextExcluded, lastClickedId: id };
    });
  }, []);

  const togglePage = useCallback((visibleIds: number[]) => {
    setState((prev) => {
      if (visibleIds.length === 0) return prev;
      if (prev.mode === "ids") {
        const allSelected = visibleIds.every((id) => prev.ids.has(id));
        const next = new Set(prev.ids);
        if (allSelected) {
          for (const id of visibleIds) next.delete(id);
        } else {
          for (const id of visibleIds) next.add(id);
        }
        return { ...prev, ids: next };
      }
      // all_filter: "all visible NOT excluded" => exclude all visible; else un-exclude all
      const noneExcluded = visibleIds.every((id) => !prev.excludedIds.has(id));
      const nextExcluded = new Set(prev.excludedIds);
      if (noneExcluded) {
        for (const id of visibleIds) nextExcluded.add(id);
      } else {
        for (const id of visibleIds) nextExcluded.delete(id);
      }
      return { ...prev, excludedIds: nextExcluded };
    });
  }, []);

  const selectRange = useCallback(
    (fromId: number, toId: number, visibleIds: number[]) => {
      const fromIdx = visibleIds.indexOf(fromId);
      const toIdx = visibleIds.indexOf(toId);
      if (fromIdx === -1) {
        // fall back to togglePage with just [toId]
        togglePage(toIdx === -1 ? [toId] : [toId]);
        setState((prev) => ({ ...prev, lastClickedId: toId }));
        return;
      }
      if (toIdx === -1) {
        togglePage([toId]);
        setState((prev) => ({ ...prev, lastClickedId: toId }));
        return;
      }
      const [start, end] = fromIdx <= toIdx ? [fromIdx, toIdx] : [toIdx, fromIdx];
      const slice = visibleIds.slice(start, end + 1);
      togglePage(slice);
      setState((prev) => ({ ...prev, lastClickedId: toId }));
    },
    [togglePage],
  );

  const selectAllFilter = useCallback((filters: Record<string, string>, total: number) => {
    setState(() => ({
      mode: "all_filter",
      ids: new Set<number>(),
      excludedIds: new Set<number>(),
      filterSnapshot: { ...filters },
      totalInFilter: total,
      lastClickedId: null,
    }));
  }, []);

  const clear = useCallback(() => {
    setState(() => ({
      mode: "ids",
      ids: new Set<number>(),
      excludedIds: new Set<number>(),
      filterSnapshot: {},
      totalInFilter: 0,
      lastClickedId: null,
    }));
  }, []);

  const materializeIds = useCallback(async (): Promise<number[]> => {
    if (state.mode === "ids") {
      const arr = [...state.ids];
      if (arr.length > MAX_BULK_IDS) {
        throw new Error("BULK_LIMIT_EXCEEDED");
      }
      return arr;
    }
    const resp = await getLeadIds(state.filterSnapshot);
    if (resp.truncated) {
      throw new Error("BULK_LIMIT_EXCEEDED");
    }
    return resp.ids.filter((id) => !state.excludedIds.has(id));
  }, [state.mode, state.ids, state.filterSnapshot, state.excludedIds]);

  const has = useCallback(
    (id: number) => {
      if (state.mode === "ids") return state.ids.has(id);
      return !state.excludedIds.has(id);
    },
    [state.mode, state.ids, state.excludedIds],
  );

  const size = useMemo(() => {
    if (state.mode === "ids") return state.ids.size;
    return Math.max(0, state.totalInFilter - state.excludedIds.size);
  }, [state.mode, state.ids, state.totalInFilter, state.excludedIds]);

  const isAllFilterMode = state.mode === "all_filter";

  return {
    mode: state.mode,
    size,
    has,
    toggle,
    selectRange,
    togglePage,
    selectAllFilter,
    clear,
    materializeIds,
    isAllFilterMode,
    filterSnapshot: state.filterSnapshot,
    totalInFilter: state.totalInFilter,
    lastClickedId: state.lastClickedId,
  };
}
