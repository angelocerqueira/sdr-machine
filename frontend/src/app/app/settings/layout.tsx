"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui";
import "./settings.css";

const SECTIONS = [
  { href: "/app/settings/perfil",       label: "Perfil",       icon: "user" as const },
  { href: "/app/settings/integracoes",  label: "Integrações",  icon: "settings" as const },
  { href: "/app/settings/targeting",    label: "Targeting",    icon: "target" as const },
  { href: "/app/settings/mcp",          label: "MCP",          icon: "bolt" as const },
  { href: "/app/settings/avancado",     label: "Avançado",     icon: "tool" as const },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isIndex = pathname === "/app/settings";

  return (
    <div className="settings-shell">
      <aside className={`settings-sidebar ${isIndex ? "settings-sidebar--mobile-only" : ""}`}>
        <header className="settings-sidebar-header">
          <h1>Configurações</h1>
        </header>
        <nav className="settings-nav">
          {SECTIONS.map((s) => {
            const active = pathname.startsWith(s.href);
            return (
              <Link
                key={s.href}
                href={s.href}
                className={`settings-nav-item ${active ? "settings-nav-item--active" : ""}`}
              >
                <Icon name={s.icon} size={16} />
                <span>{s.label}</span>
                <Icon name="chevron-r" size={14} className="settings-nav-chevron" />
              </Link>
            );
          })}
        </nav>
      </aside>
      <section className="settings-content">{children}</section>
    </div>
  );
}
