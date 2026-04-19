"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Icon, type IconName } from "@/components/ui";
import { CommandSearch } from "./command-search";
import { authClient } from "@/lib/auth-client";

const NAV_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "home", icon: "home", label: "Dashboard", href: "/app" },
  { key: "board", icon: "board", label: "Pipeline", href: "/app/kanban" },
  { key: "leads", icon: "lead", label: "Leads", href: "/app/leads" },
  { key: "job", icon: "job", label: "Jobs", href: "/app/jobs" },
];

export function AppSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: session } = authClient.useSession();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [avatarOpen, setAvatarOpen] = useState(false);
  const [theme, setThemeState] = useState(() => {
    if (typeof document !== "undefined") {
      return document.documentElement.getAttribute("data-theme") || "light";
    }
    return "light";
  });
  const avatarRef = useRef<HTMLDivElement>(null);

  const toggleTheme = useCallback(() => {
    const next = theme === "dark" ? "light" : "dark";
    setThemeState(next);
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("sdr-theme", next); } catch {}
  }, [theme]);

  // Close mobile drawer on route change
  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: close drawer on navigation
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Close avatar dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarOpen(false);
      }
    }
    if (avatarOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [avatarOpen]);

  // Cmd+K global shortcut
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const isActive = (href: string) =>
    href === "/app"
      ? pathname === "/app"
      : pathname.startsWith(href);

  return (
    <>
      {/* Mobile hamburger bar */}
      <div className="app-mobile-bar md:hidden">
        <button
          className="app-mobile-hamburger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Menu"
        >
          <Icon name={mobileOpen ? "x" : "list"} size={18} />
        </button>
        <div className="app-mobile-brand">S</div>
        <button
          className="app-mobile-hamburger"
          onClick={() => setSearchOpen(true)}
          aria-label="Buscar"
        >
          <Icon name="search" size={16} />
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <nav
        className={`app-sidebar ${mobileOpen ? "open" : ""}`}
      >
        <div className="app-sidebar-brand md:flex hidden">S</div>
        {NAV_ITEMS.map((it) => (
          <button
            key={it.key}
            className={`app-sidebar-btn ${isActive(it.href) ? "active" : ""}`}
            onClick={() => {
              router.push(it.href);
              setMobileOpen(false);
            }}
          >
            <Icon name={it.icon} size={18} />
            <span className="app-sidebar-label">{it.label}</span>
            <span className="app-sidebar-tip">{it.label}</span>
          </button>
        ))}
        <div className="app-sidebar-sep" />
        <button
          className="app-sidebar-btn"
          onClick={() => setSearchOpen(true)}
        >
          <Icon name="search" size={18} />
          <span className="app-sidebar-label">Buscar</span>
          <span className="app-sidebar-tip">Buscar</span>
        </button>
        <div ref={avatarRef} className="app-sidebar-avatar-wrap">
          <button
            className="app-sidebar-avatar"
            onClick={() => setAvatarOpen(!avatarOpen)}
          >
            {session?.user?.name
              ? session.user.name
                  .split(" ")
                  .map((w) => w[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()
              : "??"}
          </button>
          {avatarOpen && (
            <div className="app-sidebar-avatar-menu">
              <div className="avatar-menu-header">
                <div className="avatar-menu-initials">
                  {session?.user?.name
                    ? session.user.name
                        .split(" ")
                        .map((w) => w[0])
                        .join("")
                        .slice(0, 2)
                        .toUpperCase()
                    : "??"}
                </div>
                <div className="avatar-menu-info">
                  <span className="avatar-menu-name">{session?.user?.name || "Usuário"}</span>
                  <span className="avatar-menu-email">{session?.user?.email || ""}</span>
                </div>
              </div>
              <div className="avatar-menu-divider" />
              <button className="avatar-menu-item" onClick={toggleTheme}>
                <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
                <span>{theme === "dark" ? "Modo claro" : "Modo escuro"}</span>
              </button>
              <div className="avatar-menu-divider" />
              <button
                className="avatar-menu-item avatar-menu-danger"
                onClick={async () => {
                  await authClient.signOut();
                  router.push("/login");
                  router.refresh();
                }}
              >
                <Icon name="arrow-r" size={15} />
                <span>Sair</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      <CommandSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
