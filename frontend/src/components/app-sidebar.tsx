"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Icon, type IconName } from "@/components/ui";
import { CommandSearch } from "./command-search";
import { authClient } from "@/lib/auth-client";
import { getLeadsForReview } from "@/lib/api";
import { useActiveJobs } from "./use-active-jobs";
import { useToast } from "@/components/ui/toast";

const NAV_ITEMS: { key: string; icon: IconName; label: string; href: string }[] = [
  { key: "home", icon: "home", label: "Dashboard", href: "/app" },
  { key: "board", icon: "board", label: "Pipeline", href: "/app/pipeline" },
  { key: "inbox", icon: "message", label: "Inbox", href: "/app/inbox" },
  { key: "leads", icon: "lead", label: "Leads", href: "/app/leads" },
  { key: "job", icon: "job", label: "Jobs", href: "/app/jobs" },
];

function ReviewNavCount() {
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await getLeadsForReview({ per_page: 1 });
        if (active) setCount(r.total);
      } catch {
        // ignore — sidebar badge is best-effort
      }
    })();
    return () => {
      active = false;
    };
  }, []);
  if (!count) return null;
  return <span className="app-sidebar-btn-badge">{count > 99 ? "99+" : count}</span>;
}

function JobBadge() {
  const { runningCount, recentlyCompleted } = useActiveJobs();
  const announcedRef = useRef<Set<number>>(new Set());
  const { toast } = useToast();

  useEffect(() => {
    for (const job of recentlyCompleted) {
      if (announcedRef.current.has(job.id)) continue;
      announcedRef.current.add(job.id);
      if (job.status === "failed") {
        toast(`Job #${job.id} (${job.type}) falhou.`, { variant: "error" });
      } else {
        toast(`Job #${job.id} (${job.type}) concluído.`, { variant: "success" });
      }
    }
  }, [recentlyCompleted, toast]);

  if (runningCount === 0) return null;

  return <span className="app-sidebar-btn-badge">{runningCount > 99 ? "99+" : runningCount}</span>;
}

function InboxUnreadBadge() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const { listConversations } = await import("@/lib/api-inbox");
        const items = await listConversations({ filter: "unread" });
        if (!cancelled) {
          const total = items.reduce((sum, c) => sum + (c.unread_count || 0), 0);
          setCount(total);
        }
      } catch {
        // ignore
      }
    }
    poll();
    const id = setInterval(poll, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);
  if (count === 0) return null;
  return <span className="app-sidebar-btn-badge">{count > 99 ? "99+" : count}</span>;
}

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

  const isActive = (href: string) => {
    if (href === "/app") return pathname === "/app";
    // Leads nav should not highlight when on the review sub-page
    if (href === "/app/leads") return pathname.startsWith("/app/leads") && !pathname.startsWith("/app/leads/review");
    return pathname.startsWith(href);
  };

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
            aria-label={it.label}
          >
            <Icon name={it.icon} size={20} />
            {it.key === "job" && <JobBadge />}
            {it.key === "inbox" && <InboxUnreadBadge />}
            <span className="app-sidebar-tip">{it.label}</span>
          </button>
        ))}
        <button
          className={`app-sidebar-btn ${isActive("/app/leads/review") ? "active" : ""}`}
          onClick={() => {
            router.push("/app/leads/review");
            setMobileOpen(false);
          }}
          aria-label="Revisão"
        >
          <Icon name="lead" size={20} />
          <ReviewNavCount />
          <span className="app-sidebar-tip">Revisão</span>
        </button>
        <div className="app-sidebar-sep" />
        <button
          className="app-sidebar-btn"
          onClick={() => setSearchOpen(true)}
          aria-label="Buscar"
        >
          <Icon name="search" size={20} />
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
              <button
                className="avatar-menu-item"
                onClick={() => {
                  setAvatarOpen(false);
                  router.push("/app/settings");
                }}
              >
                <Icon name="settings" size={15} />
                <span>Configurações</span>
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
