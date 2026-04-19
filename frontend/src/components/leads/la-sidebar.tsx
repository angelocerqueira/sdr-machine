"use client";

import { Icon, type IconName } from "@/components/ui";

const NAV_ITEMS: { key: string; icon: IconName; label: string; active?: boolean }[] = [
  { key: "home", icon: "home", label: "Dashboard" },
  { key: "board", icon: "board", label: "Pipeline" },
  { key: "leads", icon: "lead", label: "Leads", active: true },
  { key: "job", icon: "job", label: "Jobs" },
  { key: "doc", icon: "doc", label: "Campanhas" },
];

const BOTTOM_ITEMS: { key: string; icon: IconName; label: string }[] = [
  { key: "settings", icon: "settings", label: "Settings" },
];

export function LaSidebar() {
  return (
    <nav className="la-nav">
      <div className="la-nav-brand">S</div>
      {NAV_ITEMS.map((it) => (
        <button
          key={it.key}
          className={`la-nav-btn ${it.active ? "active" : ""}`}
        >
          <Icon name={it.icon} size={18} />
          <span className="la-nav-tip">{it.label}</span>
        </button>
      ))}
      <div className="la-nav-sep" />
      {BOTTOM_ITEMS.map((it) => (
        <button key={it.key} className="la-nav-btn">
          <Icon name={it.icon} size={18} />
          <span className="la-nav-tip">{it.label}</span>
        </button>
      ))}
    </nav>
  );
}
