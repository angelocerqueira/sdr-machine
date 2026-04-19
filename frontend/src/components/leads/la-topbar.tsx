"use client";

import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "./lead-app-types";

interface LaTopbarProps {
  lead: LeadAppDetail;
  theme: string;
  setTheme: (t: string) => void;
  railOpen: boolean;
  setRailOpen: (open: boolean) => void;
  position?: number;
  total?: number;
}

export function LaTopbar({
  lead,
  theme,
  setTheme,
  railOpen,
  setRailOpen,
  position = 1,
  total = 1,
}: LaTopbarProps) {
  return (
    <div className="la-topbar">
      <div className="la-crumbs">
        <span>Leads</span>
        <span className="sep">/</span>
        <span>{lead.nicho}</span>
        <span className="sep">/</span>
        <span>{lead.cidade}</span>
        <span className="sep">/</span>
        <span className="here">#{lead.id}</span>
      </div>
      <div className="la-topbar-spacer" />
      <div className="la-topbar-nav">
        <button className="la-topbar-nav-btn" aria-label="Anterior">
          <Icon
            name="chevron-r"
            size={16}
            style={{ transform: "rotate(180deg)" }}
          />
        </button>
        <span className="la-topbar-nav-pos">{position} / {total}</span>
        <button className="la-topbar-nav-btn" aria-label="Pr\u00f3ximo">
          <Icon name="chevron-r" size={16} />
        </button>
      </div>
      <span className="la-kbd" style={{ marginLeft: 6 }}>
        J
      </span>
      <span className="la-kbd">K</span>
      <div style={{ width: 12 }} />
      <button
        className="btn btn-ghost btn-sm btn-icon la-rail-toggle"
        onClick={() => setRailOpen(!railOpen)}
        aria-label="Alternar painel lateral"
        title="Alternar painel lateral"
      >
        <Icon name={railOpen ? "sidebar-close" : "sidebar-open"} size={16} />
      </button>
      <button
        className="btn btn-ghost btn-sm btn-icon"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        aria-label="Alternar tema"
      >
        <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
      </button>
      <button
        className="btn btn-ghost btn-sm btn-icon"
        aria-label="Mais op\u00e7\u00f5es"
      >
        <Icon name="more" size={16} />
      </button>
    </div>
  );
}
