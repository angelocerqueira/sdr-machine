"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui";
import { getLeadJobs } from "@/lib/api";
import type { Job } from "@/lib/types";
import type { LeadAppDetail } from "./lead-app-types";

const JOB_TYPE_LABELS: Record<string, string> = {
  scrape: "Scrapeado",
  enrich: "Enriquecido",
  generate: "LP Gerada",
  outreach: "Outreach gerado",
};

const JOB_STATUS_ICON: Record<string, { icon: "ok" | "error" | "bolt"; color: string }> = {
  done: { icon: "ok", color: "var(--ok)" },
  failed: { icon: "error", color: "var(--danger)" },
  running: { icon: "bolt", color: "var(--accent)" },
};

function LaTimeline({ lead }: { lead: LeadAppDetail }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true); // eslint-disable-line react-hooks/set-state-in-effect -- intentional: fetch on lead change
    getLeadJobs(lead.id)
      .then(setJobs)
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, [lead.id]);

  return (
    <div className="la-info-card" style={{ gridColumn: "1 / -1" }}>
      <div className="la-info-card-head">Linha do tempo</div>
      {loading ? (
        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-muted)", fontSize: 12, padding: "8px 0" }}>
          <span className="spin" /> Carregando...
        </div>
      ) : jobs.length === 0 ? (
        <div style={{ color: "var(--text-muted)", fontSize: 12, padding: "8px 0" }}>
          Nenhum job associado a este lead.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {jobs.map((job, i) => {
            const si = JOB_STATUS_ICON[job.status] || { icon: "info" as const, color: "var(--text-muted)" };
            const date = job.finished_at || job.started_at || job.created_at;
            return (
              <div
                key={job.id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  padding: "10px 0",
                  borderBottom: i < jobs.length - 1 ? "1px solid var(--border-subtle)" : "none",
                }}
              >
                <div style={{ paddingTop: 1, flexShrink: 0 }}>
                  <Icon name={si.icon} size={14} style={{ color: si.color }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 460, color: "var(--text-body)" }}>
                    {JOB_TYPE_LABELS[job.type] || job.type}
                  </div>
                  <div
                    style={{
                      fontSize: 10,
                      color: "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                      marginTop: 2,
                    }}
                  >
                    {new Date(date).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
                <div
                  style={{
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    color: si.color,
                    fontFamily: "var(--font-mono)",
                    flexShrink: 0,
                    paddingTop: 2,
                  }}
                >
                  {job.status}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function LaTabInfo({ lead }: { lead: LeadAppDetail }) {
  const hasTech = lead.tech_stack.length > 0;
  const hasReviews = lead.top_reviews.length > 0;
  const hasAnything = hasTech || hasReviews || lead.website;

  if (!hasAnything) {
    return (
      <div>
        <div className="state" style={{ margin: "32px auto" }}>
          <div className="state-icon">
            <Icon name="info" size={20} />
          </div>
          <div className="state-title">Sem informações adicionais</div>
          <div className="state-msg">
            Execute o enriquecimento para coletar tech stack, reviews e mais dados sobre este lead.
          </div>
        </div>
        <div className="la-info-grid" style={{ marginTop: 24 }}>
          <LaTimeline lead={lead} />
        </div>
      </div>
    );
  }

  return (
    <div className="la-info-grid">
      {/* Card 1: Stack detectado */}
      {hasTech && (
        <div className="la-info-card">
          <div className="la-info-card-head">Stack detectado</div>
          <div className="la-tech-list">
            {lead.tech_stack.map((t, i) => {
              const warn = /jquery 1|bootstrap 3|wordpress 5/i.test(t.name);
              return (
                <span key={i} className={`la-tech ${warn ? "warn" : ""}`}>
                  {t.name}
                  <span className="cat">{t.category}</span>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Card 2: Top reviews */}
      {hasReviews && (
        <div className="la-info-card">
          <div className="la-info-card-head">Top reviews · Google Maps</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {lead.top_reviews.map((r, i) => (
              <div
                key={i}
                style={{
                  fontSize: 12,
                  color: "var(--text-body)",
                  lineHeight: 1.55,
                  paddingLeft: 12,
                  borderLeft: "2px solid var(--border)",
                }}
              >
                &ldquo;{r}&rdquo;
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Card 3: Timeline */}
      <LaTimeline lead={lead} />
    </div>
  );
}
