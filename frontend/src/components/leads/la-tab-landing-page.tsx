"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { getLeadLpUrl, activateLandingPage } from "@/lib/api";
import type { LeadAppDetail } from "./lead-app-types";

interface LaTabLpProps {
  lead: LeadAppDetail;
  onVersionActivated?: () => void;
}

export function LaTabLp({ lead, onVersionActivated }: LaTabLpProps) {
  const [activating, setActivating] = useState<number | null>(null);

  if (lead.lp_versions.length === 0) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="doc" size={20} />
        </div>
        <div className="state-title">Nenhuma landing page</div>
        <div className="state-msg">
          Este lead ainda não tem uma landing page gerada. Execute a etapa de geração de LP no pipeline.
        </div>
      </div>
    );
  }

  const lpUrl = getLeadLpUrl(lead.id);

  async function handleActivate(lpId: number) {
    setActivating(lpId);
    try {
      await activateLandingPage(lead.id, lpId);
      onVersionActivated?.();
    } catch (e) {
      console.error("Erro ao ativar versão:", e);
    } finally {
      setActivating(null);
    }
  }

  return (
    <div className="la-lp">
      {/* Left: Preview */}
      <div className="la-lp-preview">
        <div className="la-lp-chrome">
          <div className="la-lp-lights">
            <span />
            <span />
            <span />
          </div>
          <div className="la-lp-url">lp/{lead.public_id}</div>
          <button
            className="la-msg-icon-btn"
            title="Copiar link"
            onClick={() => navigator.clipboard.writeText(`${window.location.origin}/lp/${lead.public_id}`)}
          >
            <Icon name="copy" size={14} />
          </button>
          <a
            className="la-msg-icon-btn"
            href={`/lp/${lead.public_id}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir em nova aba"
          >
            <Icon name="external" size={14} />
          </a>
        </div>
        <div className="la-lp-frame">
          <iframe
            src={lpUrl}
            title={`LP de ${lead.nome}`}
            style={{ width: "100%", height: "100%", border: "none" }}
          />
        </div>
      </div>

      {/* Right column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
        {/* Version history */}
        <div>
          <div className="la-rail-head" style={{ marginBottom: 10 }}>
            <span>Histórico de versões</span>
          </div>
          <div className="la-versions">
            {lead.lp_versions.map((v) => (
              <div
                key={v.v}
                className={`la-version ${v.active ? "active" : ""}`}
              >
                <div className="la-version-v">v{v.v}</div>
                <div className="la-version-date">{v.created}</div>
                {v.active ? (
                  <div className="la-version-action" style={{ fontSize: 11, color: "var(--accent)" }}>
                    Ativa
                  </div>
                ) : (
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: 11 }}
                    disabled={activating === v.id}
                    onClick={() => handleActivate(v.id)}
                  >
                    {activating === v.id ? "Ativando\u2026" : "Ativar"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
