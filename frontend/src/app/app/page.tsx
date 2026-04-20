"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats, getDashboardTrends } from "@/lib/api";
import type { DashboardTrends } from "@/lib/api";
import { StatsCard } from "@/components/stats-card";
import { ProfileDistribution } from "@/components/dashboard/profile-distribution";
import { NichoDistribution } from "@/components/dashboard/nicho-distribution";
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
  disqualified: "Desqualificado",
  lp_generated: "LP Gerada",
  outreach_ready: "Msg Pronta",
  outreach_sent: "Enviada",
  responded: "Respondeu",
  in_call: "Em Call",
  closed: "Fechado",
  delivered: "Entregue",
  failed: "Falhou",
};

function scoreColor(bucket: number): string {
  if (bucket >= 80) return "var(--score-high)";
  if (bucket >= 50) return "var(--score-mid)";
  return "var(--score-low)";
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<DashboardTrends | null>(null);

  useEffect(() => {
    getDashboardStats().then(setStats);
    getDashboardTrends(14).then(setTrends).catch(() => {});
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
    <div className="p-5 md:p-6 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]">Dashboard</h2>
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
              <button
                key={status}
                onClick={() => router.push(`/kanban?status=${status}`)}
                className="rounded-lg border border-border-subtle bg-surface-raised p-4 text-center card-glow transition-default hover:border-accent/40 hover:bg-surface-overlay cursor-pointer"
              >
                <p className="text-[10px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)] mb-2">
                  {STATUS_LABELS[status] || status}
                </p>
                <p className="stat-number text-2xl font-bold">{count}</p>
              </button>
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

      {/* Classification Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <ProfileDistribution data={stats.profile_distribution ?? {}} />
        <NichoDistribution data={stats.nicho_distribution ?? {}} />
      </div>

      {/* Trends Section */}
      {trends && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
          {/* Lead Activity (bar chart) */}
          <div className="rounded-xl border border-border bg-surface p-6 lg:col-span-2">
            <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
              Atividade de leads (14 dias)
            </h3>
            {trends.leads_by_day.length > 0 ? (() => {
              const maxCount = Math.max(...trends.leads_by_day.map((d) => d.count), 1);
              return (
                <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 120 }}>
                  {trends.leads_by_day.slice(-14).map((d) => {
                    const pct = (d.count / maxCount) * 100;
                    const dayLabel = new Date(d.day + "T12:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
                    return (
                      <div
                        key={d.day}
                        style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}
                      >
                        <span
                          style={{
                            fontSize: 9,
                            fontFamily: "var(--font-mono)",
                            color: "var(--text-muted)",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {d.count > 0 ? d.count : ""}
                        </span>
                        <div
                          style={{
                            width: "100%",
                            maxWidth: 32,
                            height: `${Math.max(pct, 4)}%`,
                            background: "var(--accent)",
                            borderRadius: "3px 3px 0 0",
                            opacity: d.count > 0 ? 1 : 0.15,
                            transition: "height 0.3s ease",
                          }}
                        />
                        <span
                          style={{
                            fontSize: 8,
                            fontFamily: "var(--font-mono)",
                            color: "var(--text-subtle)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {dayLabel}
                        </span>
                      </div>
                    );
                  })}
                </div>
              );
            })() : (
              <p className="text-text-muted text-xs">Sem dados no período</p>
            )}
          </div>

          {/* Top Nichos */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
              Top nichos
            </h3>
            {trends.leads_by_nicho.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {trends.leads_by_nicho.slice(0, 8).map((n) => (
                  <div
                    key={n.nicho}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: 12,
                    }}
                  >
                    <span style={{ color: "var(--text-body)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginRight: 8 }}>
                      {n.nicho}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        fontVariantNumeric: "tabular-nums",
                        color: "var(--text-muted)",
                        background: "var(--surface-raised)",
                        padding: "2px 8px",
                        borderRadius: 99,
                        flexShrink: 0,
                      }}
                    >
                      {n.count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-text-muted text-xs">Nenhum nicho</p>
            )}
          </div>

          {/* Score Distribution */}
          <div className="rounded-xl border border-border bg-surface p-6 lg:col-span-3">
            <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
              Distribuição de scores
            </h3>
            {Object.keys(trends.score_distribution).length > 0 ? (() => {
              const buckets = Object.entries(trends.score_distribution).sort(
                ([a], [b]) => parseInt(a) - parseInt(b)
              );
              const maxVal = Math.max(...buckets.map(([, v]) => v), 1);
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {buckets.map(([bucket, count]) => {
                    const lo = parseInt(bucket);
                    const hi = Math.min(lo + 9, 100);
                    const pct = (count / maxVal) * 100;
                    return (
                      <div key={bucket} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span
                          style={{
                            width: 48,
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                            fontVariantNumeric: "tabular-nums",
                            color: "var(--text-muted)",
                            textAlign: "right",
                            flexShrink: 0,
                          }}
                        >
                          {lo}-{hi}
                        </span>
                        <div style={{ flex: 1, height: 16, background: "var(--surface-raised)", borderRadius: 4, overflow: "hidden" }}>
                          <div
                            style={{
                              height: "100%",
                              width: `${Math.max(pct, 2)}%`,
                              background: scoreColor(lo),
                              borderRadius: 4,
                              transition: "width 0.3s ease",
                            }}
                          />
                        </div>
                        <span
                          style={{
                            width: 28,
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                            fontVariantNumeric: "tabular-nums",
                            color: "var(--text-muted)",
                            textAlign: "right",
                            flexShrink: 0,
                          }}
                        >
                          {count}
                        </span>
                      </div>
                    );
                  })}
                </div>
              );
            })() : (
              <p className="text-text-muted text-xs">Sem dados de score</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
