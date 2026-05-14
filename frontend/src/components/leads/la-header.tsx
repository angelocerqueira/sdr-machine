"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { StatusPill, Tag, PipeMini } from "@/components/ui";
import type { StatusPillHandle } from "@/components/ui/status-pill";
import { ProfileBadge } from "@/components/ui/profile-badge";
import { updateLead } from "@/lib/api";
import type { LeadAppDetail } from "./lead-app-types";

interface LaHeaderProps {
  lead: LeadAppDetail;
  onLeadUpdated?: () => void;
}

export function LaHeader({ lead, onLeadUpdated }: LaHeaderProps) {
  const [optimisticStatus, setOptimisticStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const pillRef = useRef<StatusPillHandle>(null);

  const displayStatus = optimisticStatus ?? lead.status;

  // Reset optimistic state when underlying lead status catches up
  useEffect(() => {
    if (optimisticStatus && lead.status === optimisticStatus) {
      setOptimisticStatus(null);
    }
  }, [lead.status, optimisticStatus]);

  const changeStatus = useCallback(
    async (newStatus: string) => {
      if (saving || newStatus === displayStatus) return;
      const prev = displayStatus;
      setOptimisticStatus(newStatus);
      setSaving(true);
      try {
        await updateLead(lead.id, { status: newStatus });
        onLeadUpdated?.();
      } catch (e) {
        console.error("Erro ao atualizar status:", e);
        setOptimisticStatus(prev === lead.status ? null : prev);
      } finally {
        setSaving(false);
      }
    },
    [lead.id, lead.status, displayStatus, saving, onLeadUpdated],
  );

  // Keyboard shortcut `s` opens the status menu
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "s" && e.key !== "S") return;
      const t = e.target as HTMLElement;
      if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable) return;
      e.preventDefault();
      pillRef.current?.open();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="la-header">
      <div className="la-header-row1">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="la-header-name">{lead.nome}</div>
          <div className="la-header-sub">
            <span>{lead.nicho}</span>
            <span className="sep">·</span>
            <span>{lead.cidade}</span>
            <span className="sep">·</span>
            <span>{lead.telefone}</span>
            {lead.website && (
              <>
                <span className="sep">·</span>
                <a
                  href={/^https?:\/\//.test(lead.website) ? lead.website : `https://${lead.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--accent)" }}
                >
                  {lead.website}
                </a>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="la-header-row2">
        <StatusPill
          ref={pillRef}
          status={displayStatus}
          onStatusChange={changeStatus}
          disabled={saving}
        />
        {lead.perfil_lead && <ProfileBadge profile={lead.perfil_lead} size="md" />}
        <Tag icon="pin">{lead.cidade}</Tag>
        <Tag>
          {lead.rating} ★ · {lead.reviews_count}
        </Tag>
        <Tag>{lead.porte}</Tag>
        {lead.cnpj && <Tag>CNPJ ativo</Tag>}
        <div style={{ marginLeft: "auto" }} className="la-pipe-mini-wrap">
          <PipeMini current={displayStatus} onStageClick={changeStatus} />
        </div>
      </div>
    </div>
  );
}
