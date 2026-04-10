# Design System v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate SDR Machine frontend from dark-minimal DS to Apollo-like dense dark DS with Geist typography and responsive mobile-first layout shell.

**Architecture:** Replace CSS tokens in `globals.css`, swap font imports in root layout, create new TopBar component, rewrite Sidebar with grouped nav + responsive modes, update main layout shell. All pages inherit new tokens automatically.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4 (`@theme inline`), Geist + Geist Mono (via `next/font/google`)

**Spec:** `docs/superpowers/specs/2026-04-10-design-system-v2-design.md`

---

## Pre-requisite: Feature Branch

Before starting any task, create and switch to the feature branch:

```bash
git checkout -b feat/design-system-v2
```

All commits below go on this branch. PR to main at the end.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/app/globals.css` | Modify | New color/spacing/radius tokens, updated utilities |
| `src/app/layout.tsx` | Modify | Swap Outfit/DM Sans/JetBrains → Geist/Geist Mono |
| `src/components/top-bar.tsx` | Create | Fixed top bar: brand, search cmd+k, credits, CTA, avatar |
| `src/components/command-search.tsx` | Create | cmd+k modal stub (placeholder visual) |
| `src/components/sidebar.tsx` | Rewrite | Grouped nav, 3 breakpoints, drawer mobile, icon-only tablet |
| `src/app/(main)/layout.tsx` | Modify | New shell: TopBar + Sidebar + responsive main wrapper |
| `src/components/stats-card.tsx` | Modify | Update font-family refs to new tokens |
| Multiple `.tsx` files | Modify | Replace `--font-outfit` → `--font-heading` globally |
| `src/app/login/page.tsx` | Modify | Update font reference |
| `.gitignore` | Modify | Add `.superpowers/` |

---

### Task 1: Update design tokens in globals.css

**Files:**
- Modify: `src/app/globals.css`

- [ ] **Step 1: Replace `@theme inline` block with v2 tokens**

Replace the entire `@theme inline { ... }` block in `globals.css`:

```css
@theme inline {
  --color-bg: #111113;
  --color-surface: #1a1a1d;
  --color-surface-raised: #242428;
  --color-surface-overlay: #2c2c32;
  --color-border: #333339;
  --color-border-subtle: #27272d;
  --color-text: #f0f0f3;
  --color-text-secondary: #9898a3;
  --color-text-muted: #5a5a66;
  --color-accent: #34d399;
  --color-accent-dim: #059669;
  --color-accent-subtle: rgba(52, 211, 153, 0.08);
  --color-accent-glow: rgba(52, 211, 153, 0.15);
  --color-danger: #f87171;
  --color-warning: #fbbf24;
  --color-info: #60a5fa;

  --font-heading: var(--font-geist);
  --font-body: var(--font-geist);
  --font-mono: var(--font-geist-mono);
}
```

- [ ] **Step 2: Update the `.card-glow:hover` shadow to use v2 values**

```css
.card-glow:hover {
  box-shadow: 0 0 0 1px var(--color-accent-subtle), 0 4px 16px -4px rgba(0, 0, 0, 0.4);
  border-color: color-mix(in srgb, var(--color-accent) 20%, var(--color-border));
}
```

- [ ] **Step 3: Update `.skeleton` gradient to use v2 surface colors**

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-surface-raised) 25%,
    var(--color-surface-overlay) 50%,
    var(--color-surface-raised) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: 0.5rem;
}
```

(This already references CSS vars, so it inherits automatically. Verify no hardcoded colors remain.)

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds (or only pre-existing warnings).

- [ ] **Step 5: Commit**

```bash
git add src/app/globals.css
git commit -m "feat(ds): update design tokens to v2 Apollo-like palette"
```

---

### Task 2: Swap font imports in root layout

**Files:**
- Modify: `src/app/layout.tsx`

- [ ] **Step 1: Replace font imports and config**

Replace the entire file content of `src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SDR Machine",
  description: "Máquina de Prospecção Automatizada",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <body
        className={`${geist.variable} ${geistMono.variable} bg-bg text-text min-h-screen`}
      >
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds. Geist fonts load.

- [ ] **Step 3: Commit**

```bash
git add src/app/layout.tsx
git commit -m "feat(ds): swap fonts to Geist + Geist Mono"
```

---

### Task 3: Replace `--font-outfit` references globally

**Files:**
- Modify: `src/components/sidebar.tsx:51,54`
- Modify: `src/components/lead-detail.tsx:22`
- Modify: `src/app/login/page.tsx:37`
- Modify: `src/app/(main)/page.tsx:81`
- Modify: `src/app/(main)/kanban/page.tsx:10`
- Modify: `src/app/(main)/jobs/page.tsx:192`

- [ ] **Step 1: Find-and-replace all `--font-outfit` → `--font-heading` across src/**

In every `.tsx` file under `src/`, replace all occurrences of:
```
font-[family-name:var(--font-outfit)]
```
with:
```
font-[family-name:var(--font-heading)]
```

Files affected (7 files, ~9 occurrences):
- `src/components/sidebar.tsx` — lines 51, 54
- `src/components/lead-detail.tsx` — line 22
- `src/app/login/page.tsx` — line 37
- `src/app/(main)/page.tsx` — line 81
- `src/app/(main)/kanban/page.tsx` — line 10
- `src/app/(main)/jobs/page.tsx` — line 192

- [ ] **Step 2: Verify no remaining `--font-outfit` references in src/**

Run: `grep -r "font-outfit" frontend/src/ --include="*.tsx" --include="*.ts"`
Expected: No matches (only `globals.css` should have had the old var, already updated in Task 1).

- [ ] **Step 3: Run lint**

Run: `cd frontend && npm run lint`
Expected: Pass (or only pre-existing warnings).

- [ ] **Step 4: Commit**

```bash
git add -A src/
git commit -m "refactor(ds): replace --font-outfit refs with --font-heading"
```

---

### Task 4: Create TopBar component

**Files:**
- Create: `src/components/top-bar.tsx`

- [ ] **Step 1: Create `src/components/top-bar.tsx`**

```tsx
"use client";

import { useState } from "react";
import { CommandSearch } from "./command-search";

export function TopBar() {
  const [searchOpen, setSearchOpen] = useState(false);

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
          2.4k créditos
        </div>

        {/* CTA */}
        <button className="bg-accent text-bg text-xs font-semibold rounded-md px-3.5 py-1.5 hover:bg-accent-dim transition-colors duration-150 whitespace-nowrap">
          + Novo Job
        </button>

        {/* Avatar */}
        <button className="w-7 h-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-[11px] font-semibold text-text-secondary hover:border-text-muted transition-colors duration-150">
          AC
        </button>
      </header>

      <CommandSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
```

- [ ] **Step 2: Verify file compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: May show error for missing `CommandSearch` — that's ok, created in next task.

- [ ] **Step 3: Commit**

```bash
git add src/components/top-bar.tsx
git commit -m "feat(ds): create TopBar component with search, credits, CTA"
```

---

### Task 5: Create CommandSearch placeholder modal

**Files:**
- Create: `src/components/command-search.tsx`

- [ ] **Step 1: Create `src/components/command-search.tsx`**

```tsx
"use client";

import { useEffect } from "react";

interface CommandSearchProps {
  open: boolean;
  onClose: () => void;
}

export function CommandSearch({ open, onClose }: CommandSearchProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        // Toggle — parent manages state via CustomEvent or direct prop
        document.dispatchEvent(new CustomEvent("toggle-command-search"));
      }
      if (e.key === "Escape" && open) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 bg-surface border border-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted shrink-0">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3.5 3.5" />
          </svg>
          <input
            autoFocus
            type="text"
            placeholder="Buscar leads, jobs, nichos..."
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-muted outline-none"
          />
          <kbd className="font-[family-name:var(--font-mono)] text-[10px] text-text-muted bg-surface-raised border border-border rounded px-1.5 py-0.5">
            ESC
          </kbd>
        </div>
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-text-muted">Busca global em breve...</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors related to these two new files.

- [ ] **Step 3: Commit**

```bash
git add src/components/command-search.tsx
git commit -m "feat(ds): add CommandSearch placeholder modal (cmd+k)"
```

---

### Task 6: Rewrite Sidebar with grouped nav + responsive modes

**Files:**
- Rewrite: `src/components/sidebar.tsx`

- [ ] **Step 1: Rewrite `src/components/sidebar.tsx`**

```tsx
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
        href: "/",
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
        href: "/kanban",
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
        href: "/jobs",
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
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/components/sidebar.tsx
git commit -m "feat(ds): rewrite Sidebar with grouped nav, responsive breakpoints"
```

---

### Task 7: Update main layout shell

**Files:**
- Modify: `src/app/(main)/layout.tsx`

- [ ] **Step 1: Rewrite `src/app/(main)/layout.tsx`**

```tsx
import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <TopBar />
      <Sidebar />
      <main className="pt-[52px] ml-0 md:ml-14 lg:ml-[260px] transition-[margin] duration-250">
        <div className="mx-auto max-w-7xl px-4 py-6 md:px-5 md:py-7 lg:px-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
```

Note: `SignOutButton` is removed from the layout — sign out is handled by the avatar menu in TopBar (to be wired later). The standalone `SignOutButton` component remains in the codebase for reuse.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/app/\(main\)/layout.tsx
git commit -m "feat(ds): update main layout with TopBar + Sidebar shell"
```

---

### Task 8: Update stats-card.tsx for new tokens

**Files:**
- Modify: `src/components/stats-card.tsx`

- [ ] **Step 1: Update font-family reference in stats-card**

Replace the `font-[family-name:var(--font-mono)]` class — it already uses `--font-mono` which is aliased to Geist Mono in globals.css, so no change needed for font. But update the card styling for v2 density:

```tsx
interface StatsCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: boolean;
}

export function StatsCard({ label, value, icon, accent }: StatsCardProps) {
  return (
    <div className={`rounded-lg border p-4 card-glow transition-all duration-150 ${
      accent
        ? "border-accent/20 bg-accent-subtle"
        : "border-border-subtle bg-surface"
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-muted text-[10px] font-medium uppercase tracking-[0.08em] font-[family-name:var(--font-mono)]">
          {label}
        </span>
        <span className={`${accent ? "text-accent" : "text-text-muted"}`}>
          {icon}
        </span>
      </div>
      <p className={`stat-number text-2xl font-bold ${accent ? "text-accent" : "text-text"}`}>
        {value}
      </p>
    </div>
  );
}
```

Changes: `rounded-xl` → `rounded-lg`, `p-5` → `p-4`, `mb-3` → `mb-2`, `text-3xl` → `text-2xl`, `text-xs` → `text-[10px]`, added `tracking-[0.08em]`.

- [ ] **Step 2: Commit**

```bash
git add src/components/stats-card.tsx
git commit -m "feat(ds): update StatsCard density for v2"
```

---

### Task 9: Update login page font reference

**Files:**
- Modify: `src/app/login/page.tsx:37`

- [ ] **Step 1: Replace `--font-outfit` with `--font-heading` in login page**

On line 37, change:
```
font-[family-name:var(--font-outfit)]
```
to:
```
font-[family-name:var(--font-heading)]
```

(This file was already covered in Task 3's global replace, but verify it was caught.)

- [ ] **Step 2: Verify**

Run: `grep -r "font-outfit" frontend/src/`
Expected: No matches.

- [ ] **Step 3: Commit (skip if already committed in Task 3)**

---

### Task 10: Add .superpowers/ to .gitignore

**Files:**
- Modify: `.gitignore` (project root)

- [ ] **Step 1: Append `.superpowers/` to `.gitignore`**

Add this line at the end of the root `.gitignore`:

```
.superpowers/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .superpowers/ to gitignore"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run lint**

Run: `cd frontend && npm run lint`
Expected: Pass.

- [ ] **Step 2: Run full build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Visual smoke test**

Run: `cd frontend && npm run dev`
Open `http://localhost:3000` and verify:
- Top bar renders with search, CTA, credits, avatar
- Sidebar shows 3 groups (Pipeline, Dados, Config)
- Resize browser to test: mobile (drawer), tablet (icon-only 56px), desktop (full 260px)
- Dashboard page inherits new colors (darker grays, same emerald accent)
- Fonts are Geist (check via DevTools → Computed styles)

- [ ] **Step 4: Push and open PR**

```bash
git push -u origin feat/design-system-v2
```

Then open a PR to main.
