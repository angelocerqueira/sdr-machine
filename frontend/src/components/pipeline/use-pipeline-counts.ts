"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getLeadCounts } from "@/lib/api";

const POLL_INTERVAL = 5000;

interface CountsState {
  counts: Record<string, number>;
  lastTotal: number;
  staleDelta: number | null;
}

export function usePipelineCounts(filters: Record<string, string>) {
  const [state, setState] = useState<CountsState>({ counts: {}, lastTotal: 0, staleDelta: null });
  const filtersRef = useRef(filters);

  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

  const fetchAndSet = useCallback(async (markStale: boolean) => {
    try {
      const data = await getLeadCounts(filtersRef.current);
      const total = Object.values(data).reduce((a, b) => a + b, 0);
      setState((prev) => {
        if (!markStale) {
          // Filter change or explicit refresh: drop any pending stale signal —
          // it referred to the previous filter snapshot and is meaningless now.
          return { counts: data, lastTotal: total, staleDelta: null };
        }
        const delta = prev.lastTotal > 0 ? total - prev.lastTotal : 0;
        return {
          counts: data,
          lastTotal: total,
          staleDelta: Math.abs(delta) >= 1 ? delta : prev.staleDelta,
        };
      });
    } catch {
      // best-effort
    }
  }, []);

  // Initial fetch + on filter change
  useEffect(() => {
    fetchAndSet(false);
  }, [filters, fetchAndSet]);

  // Polling
  useEffect(() => {
    const id = setInterval(() => fetchAndSet(true), POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchAndSet]);

  const dismissStale = useCallback(() => {
    setState((prev) => ({ ...prev, staleDelta: null }));
  }, []);

  const refresh = useCallback(async () => {
    await fetchAndSet(false);
  }, [fetchAndSet]);

  return {
    counts: state.counts,
    total: state.lastTotal,
    staleDelta: state.staleDelta,
    dismissStale,
    refresh,
  };
}
