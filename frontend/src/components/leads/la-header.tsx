"use client";

import { StatusPill, Tag, PipeMini } from "@/components/ui";
import { ProfileBadge } from "@/components/ui/profile-badge";
import type { LeadAppDetail } from "./lead-app-types";

interface LaHeaderProps {
  lead: LeadAppDetail;
}

export function LaHeader({ lead }: LaHeaderProps) {
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
        <StatusPill status={lead.status} />
        {lead.perfil_lead && <ProfileBadge profile={lead.perfil_lead} size="md" />}
        <Tag icon="pin">{lead.cidade}</Tag>
        <Tag>
          {lead.rating} ★ · {lead.reviews_count}
        </Tag>
        <Tag>{lead.porte}</Tag>
        {lead.cnpj && <Tag>CNPJ ativo</Tag>}
        <div style={{ marginLeft: "auto" }} className="la-pipe-mini-wrap">
          <PipeMini current={lead.status} />
        </div>
      </div>
    </div>
  );
}
