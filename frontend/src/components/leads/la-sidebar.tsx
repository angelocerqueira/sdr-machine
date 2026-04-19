"use client";

import { useRouter, usePathname } from "next/navigation";
import { Icon, type IconName } from "@/components/ui";

const NAV_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "home", icon: "home", label: "Dashboard", href: "/app" },
  { key: "board", icon: "board", label: "Pipeline", href: "/app/kanban" },
  { key: "leads", icon: "lead", label: "Leads", href: "/app/leads" },
  { key: "job", icon: "job", label: "Jobs", href: "/app/jobs" },
  { key: "doc", icon: "doc", label: "Campanhas", href: "/app" },
];

const BOTTOM_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "settings", icon: "settings", label: "Configurações", href: "/app" },
];

export function LaSidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/app/leads"
      ? pathname.startsWith("/app/leads")
      : pathname === href;

  return (
    <nav className="la-nav">
      <div className="la-nav-brand">S</div>
      {NAV_ITEMS.map((it) => (
        <button
          key={it.key}
          className={`la-nav-btn ${isActive(it.href) ? "active" : ""}`}
          onClick={() => router.push(it.href)}
        >
          <Icon name={it.icon} size={18} />
          <span className="la-nav-tip">{it.label}</span>
        </button>
      ))}
      <div className="la-nav-sep" />
      {BOTTOM_ITEMS.map((it) => (
        <button
          key={it.key}
          className="la-nav-btn"
          onClick={() => router.push(it.href)}
        >
          <Icon name={it.icon} size={18} />
          <span className="la-nav-tip">{it.label}</span>
        </button>
      ))}
    </nav>
  );
}
