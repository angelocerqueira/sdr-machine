"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: DashboardIcon },
  { href: "/kanban", label: "Kanban", icon: KanbanIcon },
  { href: "/jobs", label: "Jobs", icon: JobsIcon },
];

function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
    </svg>
  );
}

function KanbanIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <rect x="1.5" y="1.5" width="3.5" height="13" rx="1" />
      <rect x="6.25" y="1.5" width="3.5" height="9" rx="1" />
      <rect x="11" y="1.5" width="3.5" height="11" rx="1" />
    </svg>
  );
}

function JobsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="6.5" />
      <path d="M8 4.5v4l2.5 1.5" />
    </svg>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] shrink-0 border-r border-border bg-surface flex flex-col min-h-screen">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-dim flex items-center justify-center">
            <span className="text-bg text-xs font-bold font-[family-name:var(--font-outfit)]">S</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-text font-[family-name:var(--font-outfit)] tracking-tight">SDR Machine</h1>
            <p className="text-[10px] text-text-muted font-[family-name:var(--font-mono)] tracking-wide">v1.0</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-border" />

      {/* Navigation */}
      <nav className="flex flex-col gap-0.5 px-3 pt-4">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-default ${
                active
                  ? "text-text bg-surface-raised"
                  : "text-text-secondary hover:text-text hover:bg-surface-raised/50"
              }`}
            >
              {/* Active indicator */}
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-accent" />
              )}
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom spacer */}
      <div className="mt-auto px-5 pb-5">
        <div className="rounded-lg border border-border-subtle bg-surface-raised/50 p-3">
          <p className="text-[10px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)] mb-1">Pipeline</p>
          <p className="text-xs text-text-secondary">Pronto para prospectar</p>
        </div>
      </div>
    </aside>
  );
}
