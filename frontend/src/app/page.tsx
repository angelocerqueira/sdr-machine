"use client";

import { useEffect, useState } from "react";
import { getDashboardStats } from "@/lib/api";
import { StatsCard } from "@/components/stats-card";
import type { DashboardStats } from "@/lib/types";

function LeadsIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="7" cy="6" r="3" />
      <path d="M1 16c0-3 2.5-5 6-5s6 2 6 5" />
      <circle cx="15" cy="6" r="2" />
      <path d="M14 11c2 0 4.5 1.2 4.5 3.5" />
    </svg>
  );
}

function ScoreIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <polyline points="2,16 6,10 10,13 14,6 18,2" />
    </svg>
  );
}

function JobsIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <rect x="2" y="2" width="16" height="16" rx="3" />
      <path d="M6 10h8M6 14h5" />
    </svg>
  );
}

function ConversionIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M5 10l3 3 7-7" />
      <circle cx="10" cy="10" r="8" />
    </svg>
  );
}

const STATUS_LABELS: Record<string, string> = {
  scraped: "Scrapeado",
  enriched: "Analisado",
  lp_generated: "LP Gerada",
  outreach_ready: "Msg Pronta",
  outreach_sent: "Enviada",
  responded: "Respondeu",
  in_call: "Em Call",
  closed: "Fechado",
  delivered: "Entregue",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getDashboardStats().then(setStats);
  }, []);

  if (!stats) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-outfit)]">Dashboard</h2>
        <p className="text-text-secondary text-sm mt-1">Visão geral da prospecção</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard label="Total Leads" value={stats.total_leads} icon={<LeadsIcon />} />
        <StatsCard label="Score Médio" value={stats.avg_score ?? "—"} icon={<ScoreIcon />} />
        <StatsCard label="Total Jobs" value={stats.total_jobs} icon={<JobsIcon />} />
        <StatsCard
          label="Conversão"
          value={stats.conversion_rate ? `${stats.conversion_rate}%` : "—"}
          icon={<ConversionIcon />}
          accent
        />
      </div>

      {/* Leads por Status */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
          Leads por Status
        </h3>
        {Object.keys(stats.leads_by_status).length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(stats.leads_by_status).map(([status, count]) => (
              <div
                key={status}
                className="rounded-lg border border-border-subtle bg-surface-raised p-4 text-center card-glow transition-default"
              >
                <p className="text-[10px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)] mb-2">
                  {STATUS_LABELS[status] || status}
                </p>
                <p className="stat-number text-2xl font-bold">{count}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-12 h-12 rounded-full bg-surface-raised border border-border flex items-center justify-center mb-4">
              <LeadsIcon />
            </div>
            <p className="text-text-secondary text-sm">Nenhum lead ainda</p>
            <p className="text-text-muted text-xs mt-1">Execute o scraping no Kanban para começar</p>
          </div>
        )}
      </div>
    </div>
  );
}
