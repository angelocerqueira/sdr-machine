"use client";

import type { Lead } from "@/lib/types";
import { getLeadLpUrl } from "@/lib/api";

interface LeadDetailProps {
  lead: Lead;
}

export function LeadDetail({ lead }: LeadDetailProps) {
  const score = lead.opportunity_score ?? 0;
  const scoreClass = score >= 60 ? "text-accent" : score >= 40 ? "text-warning" : "text-text-muted";
  const scoreBg = score >= 60 ? "bg-accent-subtle border-accent/20" : score >= 40 ? "bg-warning/5 border-warning/20" : "bg-surface-raised border-border";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-outfit)]">{lead.nome}</h2>
          <p className="text-text-secondary text-sm mt-1">
            {lead.categoria || lead.nicho} · {lead.cidade}
          </p>
        </div>
        <div className={`text-center rounded-xl border px-5 py-3 ${scoreBg}`}>
          <p className={`stat-number text-3xl font-bold ${scoreClass}`}>{lead.opportunity_score ?? "—"}</p>
          <p className="text-[10px] text-text-muted uppercase tracking-widest font-[family-name:var(--font-mono)] mt-1">Score</p>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Telefone", value: lead.telefone || "—" },
          { label: "Rating", value: lead.rating ? `${lead.rating} (${lead.reviews_count} reviews)` : "—" },
          { label: "Website", value: lead.website || "Sem site" },
          { label: "Status", value: lead.status },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-border bg-surface p-4">
            <p className="text-[10px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)] mb-1.5">{label}</p>
            <p className="text-[13px] text-text truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Gaps */}
      {lead.opportunity_reasons.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-4">
            Gaps Detectados
          </h3>
          <div className="space-y-2">
            {lead.opportunity_reasons.map((reason, i) => (
              <div key={i} className="flex items-center gap-3 text-[13px] text-text-secondary">
                <span className="w-1.5 h-1.5 rounded-full bg-danger shrink-0" />
                {reason}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LP Preview */}
      {lead.lp_html && (
        <div className="rounded-xl border border-border bg-surface overflow-hidden">
          <div className="px-5 py-3 border-b border-border-subtle flex items-center gap-3">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-danger/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-warning/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-accent/60" />
            </div>
            <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-mono)]">
              Preview da LP
            </h3>
          </div>
          <iframe
            src={getLeadLpUrl(lead.id)}
            className="w-full h-[500px] bg-white"
            title={`LP Preview - ${lead.nome}`}
          />
        </div>
      )}
    </div>
  );
}
