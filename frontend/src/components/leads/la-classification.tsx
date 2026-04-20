"use client";

import { useState } from "react";
import { ProfileBadge } from "@/components/ui/profile-badge";
import { NICHO_LABEL, type NichoCanonico } from "@/lib/types";
import { reclassifyLead } from "@/lib/api";
import type { LeadAppDetail } from "./lead-app-types";

export function LaClassification({
  lead,
  onLeadUpdated,
}: {
  lead: LeadAppDetail;
  onLeadUpdated?: () => void;
}) {
  const [loading, setLoading] = useState(false);

  async function handleReclassify() {
    setLoading(true);
    try {
      await reclassifyLead(lead.id);
      onLeadUpdated?.();
    } catch (err) {
      console.error("Reclassify failed:", err);
    } finally {
      setLoading(false);
    }
  }

  const confidencePct = Math.round((lead.nicho_confidence ?? 0) * 100);

  return (
    <div className="la-rail-section">
      <div className="la-rail-head">
        <span>Classificação</span>
        <button
          className="la-btn-inline"
          disabled={loading}
          onClick={handleReclassify}
        >
          {loading ? "Re-classificando..." : "Re-classificar"}
        </button>
      </div>

      <dl className="la-classification-grid">
        <dt>Perfil</dt>
        <dd>
          {lead.perfil_lead ? (
            <ProfileBadge profile={lead.perfil_lead} size="md" />
          ) : (
            <span className="la-muted">—</span>
          )}
        </dd>

        <dt>Nicho</dt>
        <dd>
          {lead.nicho_canonico ? (
            <>
              <span>{NICHO_LABEL[lead.nicho_canonico as NichoCanonico]}</span>
              {lead.nicho_source && (
                <span
                  className="la-source-tag"
                  title={`Fonte da classificação: ${lead.nicho_source}`}
                >
                  {lead.nicho_source}
                </span>
              )}
            </>
          ) : (
            <span className="la-muted">—</span>
          )}
        </dd>

        <dt>Confiança</dt>
        <dd>
          <div
            className="la-confidence-bar"
            aria-label={`Confiança ${confidencePct}%`}
          >
            <div
              className="la-confidence-fill"
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <span className="la-confidence-value">{confidencePct}%</span>
        </dd>

        <dt>Pacote</dt>
        <dd>
          {lead.pacote_sugerido ? (
            <span>{lead.pacote_sugerido}</span>
          ) : (
            <span className="la-muted">—</span>
          )}
        </dd>

        <dt>Prioridade</dt>
        <dd>
          {lead.prioridade ? (
            <span>{lead.prioridade}</span>
          ) : (
            <span className="la-muted">—</span>
          )}
        </dd>
      </dl>
    </div>
  );
}
