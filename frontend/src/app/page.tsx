"use client";

import { useEffect, useState } from "react";
import { getDashboardStats } from "@/lib/api";
import { StatsCard } from "@/components/stats-card";
import type { DashboardStats } from "@/lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getDashboardStats().then(setStats);
  }, []);

  if (!stats) return <div className="text-zinc-400">Carregando...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard label="Total Leads" value={stats.total_leads} icon="👥" />
        <StatsCard label="Score Médio" value={stats.avg_score ?? "—"} icon="📈" />
        <StatsCard label="Total Jobs" value={stats.total_jobs} icon="⚙️" />
        <StatsCard
          label="Conversão"
          value={stats.conversion_rate ? `${stats.conversion_rate}%` : "—"}
          icon="✅"
        />
      </div>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h3 className="text-lg font-semibold mb-4">Leads por Status</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.entries(stats.leads_by_status).map(([status, count]) => (
            <div key={status} className="bg-zinc-800 rounded-lg p-3 text-center">
              <p className="text-xs text-zinc-400 mb-1">{status}</p>
              <p className="text-xl font-bold">{count}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
