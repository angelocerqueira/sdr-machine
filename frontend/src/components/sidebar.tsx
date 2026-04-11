"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    label: "Pipeline",
    items: [
      {
        href: "/app",
        label: "Dashboard",
        icon: (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <rect x="1.5" y="1.5" width="5" height="5" rx="1" />
            <rect x="9.5" y="1.5" width="5" height="5" rx="1" />
            <rect x="1.5" y="9.5" width="5" height="5" rx="1" />
            <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
          </svg>
        ),
      },
      {
        href: "/app/kanban",
        label: "Kanban",
        icon: (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <rect x="1.5" y="1.5" width="3.5" height="13" rx="1" />
            <rect x="6.25" y="1.5" width="3.5" height="9" rx="1" />
            <rect x="11" y="1.5" width="3.5" height="11" rx="1" />
          </svg>
        ),
      },
      {
        href: "/app/jobs",
        label: "Jobs",
        icon: (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="8" cy="8" r="6.5" />
            <path d="M8 4.5v4l2.5 1.5" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Dados",
    items: [
      {
        href: "/leads",
        label: "Leads",
        icon: (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="6" cy="5" r="2.5" />
            <path d="M1 14c0-2.5 2-4.5 5-4.5s5 2 5 4.5" />
            <circle cx="12" cy="5.5" r="1.8" />
            <path d="M12 9.5c1.5 0 3 1 3 2.5" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Config",
    items: [
      {
        href: "/settings",
        label: "Settings",
        icon: (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="8" cy="8" r="2" />
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2M2.9 2.9l1.4 1.4M11.7 11.7l1.4 1.4M2.9 13.1l1.4-1.4M11.7 4.3l1.4-1.4" />
          </svg>
        ),
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Listen for toggle events from TopBar hamburger
  useEffect(() => {
    function handleToggle() {
      setMobileOpen((prev) => !prev);
    }
    document.addEventListener("toggle-sidebar", handleToggle);
    return () => document.removeEventListener("toggle-sidebar", handleToggle);
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMobileOpen(false);
  }, [pathname]);

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-80 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed top-[52px] bottom-0 left-0 bg-surface border-r border-border z-90 flex flex-col overflow-y-auto transition-transform duration-250 ease-out
          w-[260px]
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0 md:w-14
          lg:w-[260px]
        `}
      >
        {/* Nav sections */}
        <nav className="flex-1 py-2">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="mb-1">
              <p className="hidden lg:block font-[family-name:var(--font-mono)] text-[10px] font-medium uppercase tracking-[0.1em] text-text-muted px-4 pt-3 pb-1.5">
                {section.label}
              </p>
              {section.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group relative flex items-center gap-2.5 mx-2 rounded-md transition-all duration-150
                      px-3 py-2
                      md:justify-center md:px-0 md:py-2.5 md:mx-1.5
                      lg:justify-start lg:px-3 lg:py-2 lg:mx-2
                      ${active
                        ? "bg-surface-raised text-text"
                        : "text-text-secondary hover:bg-surface-raised hover:text-text"
                      }
                    `}
                  >
                    {/* Active indicator — hidden on tablet icon-only */}
                    {active && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-accent hidden lg:block" />
                    )}
                    <span className={`shrink-0 ${active ? "opacity-100" : "opacity-60 group-hover:opacity-90"}`}>
                      {item.icon}
                    </span>
                    <span className="text-[13px] font-medium md:hidden lg:inline">
                      {item.label}
                    </span>
                    {item.badge !== undefined && (
                      <span className="ml-auto font-[family-name:var(--font-mono)] text-[10px] font-medium bg-accent-subtle text-accent rounded-full px-1.5 py-0.5 md:hidden lg:inline">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Bottom status — desktop only */}
        <div className="hidden lg:block border-t border-border-subtle px-4 py-3">
          <p className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.08em] text-text-muted mb-1">
            Pipeline
          </p>
          <p className="text-xs text-text-secondary">Pronto para prospectar</p>
        </div>
      </aside>
    </>
  );
}
