"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { CommandSearch } from "./command-search";
import { SignOutButton } from "./sign-out-button";

export function TopBar() {
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [avatarOpen, setAvatarOpen] = useState(false);
  const [totalLeads, setTotalLeads] = useState<number | null>(null);
  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    import("@/lib/api").then(({ getDashboardStats }) => {
      getDashboardStats()
        .then((s) => setTotalLeads(s.total_leads))
        .catch(() => {});
    });
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarOpen(false);
      }
    }
    if (avatarOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [avatarOpen]);

  return (
    <>
      <header className="fixed top-0 left-0 right-0 h-[52px] bg-surface border-b border-border flex items-center px-4 gap-3 z-100">
        {/* Hamburger — mobile only */}
        <button
          className="md:hidden w-8 h-8 flex items-center justify-center rounded-md text-text-secondary hover:bg-surface-raised hover:text-text transition-all duration-150"
          onClick={() => document.dispatchEvent(new CustomEvent("toggle-sidebar"))}
          aria-label="Menu"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M3 5h12M3 9h12M3 13h12" />
          </svg>
        </button>

        {/* Brand */}
        <div className="flex items-center gap-2 mr-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent to-accent-dim flex items-center justify-center">
            <span className="text-bg text-[10px] font-bold font-[family-name:var(--font-heading)]">S</span>
          </div>
          <span className="hidden lg:inline text-sm font-semibold tracking-tight">SDR Machine</span>
        </div>

        {/* Search trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="flex-1 max-w-[420px] h-8 bg-surface-raised border border-border-subtle rounded-md flex items-center px-2.5 gap-2 cursor-pointer hover:border-border transition-colors duration-150"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted shrink-0">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3.5 3.5" />
          </svg>
          <span className="text-text-muted text-xs flex-1 text-left">Buscar leads, jobs...</span>
          <kbd className="hidden sm:inline font-[family-name:var(--font-mono)] text-[10px] text-text-muted bg-surface-overlay border border-border rounded px-1.5 py-0.5">
            ⌘K
          </kbd>
        </button>

        <div className="flex-1" />

        {/* Credits */}
        <div className="hidden md:flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-[11px] text-text-muted bg-surface-raised border border-border-subtle rounded-md px-2.5 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          {totalLeads !== null ? `${totalLeads} leads` : "..."}
        </div>

        {/* CTA */}
        <button
          className="bg-accent text-bg text-xs font-semibold rounded-md px-3.5 py-1.5 hover:bg-accent-dim transition-colors duration-150 whitespace-nowrap"
          onClick={() => router.push("/app/kanban")}
        >
          + Novo Job
        </button>

        {/* Avatar + dropdown */}
        <div ref={avatarRef} className="relative">
          <button
            onClick={() => setAvatarOpen((v) => !v)}
            className="w-7 h-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-[11px] font-semibold text-text-secondary hover:border-text-muted transition-colors duration-150"
          >
            AC
          </button>
          {avatarOpen && (
            <div className="absolute right-0 top-[calc(100%+6px)] bg-surface-overlay border border-border rounded-md shadow-lg py-1.5 px-2 min-w-[120px] z-50">
              <SignOutButton />
            </div>
          )}
        </div>
      </header>

      <CommandSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
