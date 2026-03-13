"use client";

import type { Lead } from "@/lib/types";
import { getLeadLpUrl } from "@/lib/api";

interface LeadDetailProps {
  lead: Lead;
}

export function LeadDetail({ lead }: LeadDetailProps) {
  const scoreColor =
    (lead.opportunity_score ?? 0) >= 60 ? "text-green-400" :
    (lead.opportunity_score ?? 0) >= 40 ? "text-yellow-400" : "text-zinc-400";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">{lead.nome}</h2>
          <p className="text-zinc-400 text-sm mt-1">
            {lead.categoria || lead.nicho} · {lead.cidade}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${scoreColor}`}>{lead.opportunity_score ?? "—"}</p>
          <p className="text-xs text-zinc-500">Score</p>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Telefone", value: lead.telefone },
          { label: "Rating", value: lead.rating ? `${lead.rating}⭐ (${lead.reviews_count})` : "—" },
          { label: "Website", value: lead.website || "Sem site" },
          { label: "Status", value: lead.status },
        ].map(({ label, value }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
            <p className="text-xs text-zinc-400 mb-1">{label}</p>
            <p className="text-sm truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Gaps */}
      {lead.opportunity_reasons.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-3">Gaps Detectados</h3>
          <ul className="space-y-1">
            {lead.opportunity_reasons.map((reason, i) => (
              <li key={i} className="text-sm text-zinc-300 flex items-center gap-2">
                <span className="text-red-400">•</span> {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* LP Preview */}
      {lead.lp_html && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-3">Preview da LP</h3>
          <iframe
            src={getLeadLpUrl(lead.id)}
            className="w-full h-[500px] rounded-lg border border-zinc-700"
            title={`LP Preview - ${lead.nome}`}
          />
        </div>
      )}
    </div>
  );
}
