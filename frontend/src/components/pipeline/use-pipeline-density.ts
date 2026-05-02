"use client";

import { useCallback, useEffect, useState } from "react";

export type PipelineDensity = "compact" | "comfortable";

const STORAGE_KEY = "sdr-pipeline-density";

export function readStoredDensity(): PipelineDensity {
  if (typeof window === "undefined") return "compact";
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === "comfortable" ? "comfortable" : "compact";
  } catch {
    return "compact";
  }
}

export function persistDensity(density: PipelineDensity) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, density);
  } catch {
    // localStorage unavailable
  }
}

/**
 * Owns density state. Call ONCE per page (in PipelinePage), then thread
 * `density` + `toggle` down via props. Multiple instances would split state.
 */
export function usePipelineDensity() {
  const [density, setDensity] = useState<PipelineDensity>(readStoredDensity);

  useEffect(() => {
    persistDensity(density);
  }, [density]);

  const toggle = useCallback(() => {
    setDensity((prev) => (prev === "compact" ? "comfortable" : "compact"));
  }, []);

  return { density, toggle, setDensity };
}
