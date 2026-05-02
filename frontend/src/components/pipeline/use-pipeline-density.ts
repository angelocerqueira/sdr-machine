"use client";

import { useCallback, useEffect, useState } from "react";

export type PipelineDensity = "compact" | "comfortable";

const STORAGE_KEY = "sdr-pipeline-density";

function readStored(): PipelineDensity {
  if (typeof window === "undefined") return "compact";
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === "comfortable" ? "comfortable" : "compact";
  } catch {
    return "compact";
  }
}

export function usePipelineDensity() {
  const [density, setDensity] = useState<PipelineDensity>(readStored);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, density);
    } catch {
      // localStorage unavailable
    }
  }, [density]);

  const toggle = useCallback(() => {
    setDensity((prev) => (prev === "compact" ? "comfortable" : "compact"));
  }, []);

  return { density, toggle, setDensity };
}
