"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getJobs } from "@/lib/api";
import type { Job } from "@/lib/types";

const POLL_INTERVAL = 5000;

export interface ActiveJobsState {
  runningCount: number;
  recentlyCompleted: Job[]; // jobs that transitioned from running -> done/failed in the last poll
}

interface RawSnapshot {
  ids: Set<number>;
  byId: Map<number, Job>;
}

export function useActiveJobs() {
  const [state, setState] = useState<ActiveJobsState>({ runningCount: 0, recentlyCompleted: [] });
  const lastSnapshotRef = useRef<RawSnapshot>({ ids: new Set(), byId: new Map() });

  const tick = useCallback(async () => {
    try {
      // Fetch enough recent jobs to detect transitions. The API doesn't filter by status,
      // so grab the last 50 and partition.
      const data = await getJobs({ per_page: "50" });
      const items = data.items ?? [];

      const running = items.filter((j) => j.status === "running" || j.status === "pending");
      const newRunningIds = new Set(running.map((j) => j.id));
      const newById = new Map(items.map((j) => [j.id, j]));

      // Find jobs that were running before but are now in a terminal state.
      const prev = lastSnapshotRef.current;
      const newlyCompleted: Job[] = [];
      for (const prevId of prev.ids) {
        if (!newRunningIds.has(prevId)) {
          const cur = newById.get(prevId);
          if (cur && cur.status !== "running" && cur.status !== "pending") {
            newlyCompleted.push(cur);
          }
        }
      }

      lastSnapshotRef.current = { ids: newRunningIds, byId: newById };
      setState({ runningCount: running.length, recentlyCompleted: newlyCompleted });
    } catch {
      // best-effort
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: kick off initial poll
    tick();
    const id = setInterval(tick, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [tick]);

  return state;
}
