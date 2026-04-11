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
                    {/* Tooltip — tablet icon-only mode */}
                    <span className="pointer-events-none absolute left-full ml-2 top-1/2 -translate-y-1/2 hidden md:group-hover:flex lg:!hidden whitespace-nowrap bg-surface-overlay border border-border text-text text-xs font-medium rounded-md px-2.5 py-1 shadow-lg z-50">
                      {item.label}
                    </span>
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
