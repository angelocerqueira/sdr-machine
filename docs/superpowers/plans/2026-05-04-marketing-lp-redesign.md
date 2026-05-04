# Marketing LP Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir a LP marketing atual por uma versão alinhada à DS Instrumento (dark, paper-on-ink), com hero astrolábio SVG, copy "Pare de pagar SDR pra abrir LinkedIn", promessa em 4 atos, demo interativa redesenhada e Calendly embed inline.

**Architecture:** Pure frontend (Next.js 16 + React 19 + Tailwind v4). Sections compostas em `src/app/(marketing)/page.tsx`. Componentes novos em `src/components/marketing/`. Motion via Framer Motion + IntersectionObserver hooks reutilizáveis. Calendly embed via script oficial. LP escopa dark theme via classe CSS local (não tinka o `<html data-theme>`, não afeta app autenticado).

**Tech Stack:** Next.js 16 App Router · React 19 · TypeScript 5 strict · Tailwind v4 (CSS vars + `@theme inline`) · Framer Motion · CSS Modules pra SVG-heavy hero · DS Instrumento tokens.

**Spec:** `docs/superpowers/specs/2026-05-04-marketing-lp-redesign-design.md`

---

## Notas de execução

- Branch já criado: `feat/marketing-lp-redesign`. Trabalhe nela.
- Sem suite de testes frontend. Verificação = lint + build + dev server visual em desktop (1280px) e mobile (375px).
- DS Instrumento tokens já existem em `globals.css`. NÃO criar tokens duplicados. Use `bg-paper-0`, `text-text`, `border-border-subtle`, `bg-accent` etc.
- Cores específicas (warn=mostarda, danger=terracota, ok=salvia) já mapeadas no Tailwind v4 via `@theme inline`. Se algum token semântico não estiver no `@theme inline` (ex.: `text-warn`), use `style={{ color: "var(--warn)" }}` ao invés de inventar utilitário.
- Commitar a cada task. Sem `--no-verify`.

---

## Task 1: Escopar dark theme à LP marketing + env var Calendly

**Estratégia:** Em vez de mudar `<html data-theme="dark">` (afeta o app inteiro e gera FOUC), criar uma classe CSS `.theme-marketing-dark` que duplica os tokens dark e wrappar o layout marketing nela. Zero JS, zero XSS surface, zero FOUC.

**Files:**
- Modify: `frontend/src/app/globals.css` (adicionar bloco `.theme-marketing-dark`)
- Modify: `frontend/src/app/(marketing)/layout.tsx` (wrappar children)
- Create or Modify: `frontend/.env.local.example`

- [ ] **Step 1: Adicionar `.theme-marketing-dark` ao globals.css**

Localize em `frontend/src/app/globals.css` o bloco `[data-theme="dark"] { ... }`. Logo abaixo dele, adicione:

```css
/* ---- Scoped dark theme — usado SOMENTE pela LP marketing ---- */
.theme-marketing-dark {
  --paper-0: #0E0E0D;
  --paper-1: #161614;
  --paper-2: #1D1D1B;
  --paper-3: #252523;
  --ink-0: #F5F3EC;
  --ink-1: #E5E3DA;
  --ink-2: #C4C2B6;
  --ink-3: #8F8E83;
  --ink-4: #6B6A62;
  --ink-5: #3E3D39;
  --line-1: #242421;
  --line-2: #302F2C;
  --line-3: #4A4945;
  --accent: oklch(0.66 0.16 var(--accent-h));
  --accent-hover: oklch(0.72 0.16 var(--accent-h));
  --accent-soft: oklch(0.22 0.08 var(--accent-h));
  --accent-line: oklch(0.32 0.12 var(--accent-h));
  --accent-ink: oklch(0.82 0.14 var(--accent-h));
  --ok: oklch(0.70 0.13 155);
  --ok-soft: oklch(0.22 0.05 155);
  --warn: oklch(0.76 0.13 70);
  --warn-soft: oklch(0.22 0.06 70);
  --danger: oklch(0.66 0.16 25);
  --danger-soft: oklch(0.22 0.06 25);
  --score-high: oklch(0.68 0.17 25);
  --score-mid: oklch(0.76 0.13 70);
  --score-low: oklch(0.70 0.13 155);
  --shadow-1: 0 1px 0 rgba(0, 0, 0, 0.4);
  --shadow-2: 0 1px 2px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.04);
  --shadow-3: 0 2px 8px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.04);
  --shadow-4: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.04);

  background: var(--paper-0);
  color: var(--ink-0);
  color-scheme: dark;
}
```

**Importante:** Esses tokens são cópia direta do bloco `[data-theme="dark"]` existente. Se aquele bloco for atualizado no futuro, sincronize aqui. Comente isso na linha de abertura.

- [ ] **Step 2: Wrappar o layout marketing**

Edit `frontend/src/app/(marketing)/layout.tsx`:

```tsx
import { MarketingNavbar } from "@/components/marketing/marketing-navbar";

export const metadata = {
  title: "SDR Machine — Instrumento de prospecção B2B",
  description:
    "Acha o lead, lê o site, prepara a abordagem e abre a conversa. Pare de pagar SDR pra abrir LinkedIn.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-marketing-dark min-h-screen">
      <MarketingNavbar />
      {children}
    </div>
  );
}
```

- [ ] **Step 3: Criar/atualizar `frontend/.env.local.example`**

Verifique se existe. Se sim, adicione a linha. Se não, crie:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sdr_machine
NEXT_PUBLIC_CALENDLY_URL=https://calendly.com/seu-usuario/demo-15min
```

- [ ] **Step 4: Verificar visualmente**

Run: `cd frontend && npm run dev`
1. Abrir `http://localhost:3000/` — deve renderizar dark mesmo se localStorage tiver `sdr-theme: light`.
2. Abrir `http://localhost:3000/app` — deve respeitar toggle (light por padrão).

- [ ] **Step 5: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/app/\(marketing\)/layout.tsx frontend/.env.local.example
git commit -m "feat(marketing): escopar dark theme à LP via .theme-marketing-dark"
```

---

## Task 2: Hooks de motion reutilizáveis

**Files:**
- Create: `frontend/src/components/marketing/lp-motion.ts`

- [ ] **Step 1: Escrever `lp-motion.ts` com 4 hooks**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

export function useFadeUpOnView<T extends HTMLElement = HTMLDivElement>(threshold = 0.2) {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [threshold]);

  return { ref, visible };
}

export function useCountUp(target: number, duration = 800) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
          obs.disconnect();
        }
      },
      { threshold: 0.5 }
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setValue(target);
      return;
    }
    const start = performance.now();
    let raf: number;
    function tick(now: number) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [started, target, duration]);

  return { ref, value };
}

export function useMockupLoop(max: number, intervalMs = 4000) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % max);
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [max, intervalMs]);

  return index;
}

export const lpEase = [0.16, 1, 0.3, 1] as const;
export const lpDuration = { fast: 0.25, base: 0.4, slow: 0.6 } as const;
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/lp-motion.ts
git commit -m "feat(marketing): hooks de motion (fade-up, count-up, mockup-loop)"
```

---

## Task 3: Hero — astrolábio SVG e copy

**Files:**
- Create: `frontend/src/components/marketing/hero-astrolabe.tsx`
- Create: `frontend/src/components/marketing/hero-astrolabe.module.css`

- [ ] **Step 1: Criar CSS module**

`frontend/src/components/marketing/hero-astrolabe.module.css`:

```css
.heroRoot {
  position: relative;
  min-height: 92vh;
  background: var(--paper-0);
  color: var(--ink-0);
  overflow: hidden;
  isolation: isolate;
}

.heroRoot::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 80% at 80% 30%, oklch(0.66 0.16 256 / 0.08), transparent 70%),
    radial-gradient(ellipse 50% 60% at 20% 70%, oklch(0.76 0.13 70 / 0.06), transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.grain {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.012) 0px, transparent 1px, transparent 2px),
    repeating-linear-gradient(90deg, rgba(255,255,255,0.012) 0px, transparent 1px, transparent 2px);
  pointer-events: none;
  z-index: 0;
}

.body {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 72px 24px 96px;
  display: grid;
  gap: 48px;
  align-items: center;
}

@media (min-width: 1024px) {
  .body {
    grid-template-columns: 1.15fr 1fr;
    padding: 96px 32px;
    gap: 64px;
  }
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--warn);
  text-transform: uppercase;
  margin-bottom: 22px;
}

.eyebrow::before {
  content: "";
  width: 18px;
  height: 1px;
  background: var(--warn);
}

.h1 {
  font-family: var(--font-sans);
  font-weight: 480;
  font-size: clamp(36px, 6vw, 56px);
  letter-spacing: -0.028em;
  line-height: 1;
  margin: 0 0 22px;
  color: var(--ink-0);
  max-width: 580px;
}

.sub {
  font-size: 15px;
  line-height: 1.55;
  color: var(--ink-2);
  margin-bottom: 30px;
  max-width: 480px;
}

.ctas {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.btnPri {
  background: var(--accent);
  color: var(--paper-0);
  padding: 13px 22px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 13px;
  box-shadow: 0 8px 24px oklch(0.66 0.16 256 / 0.25);
  transition: filter 0.2s;
}

.btnPri:hover { filter: brightness(1.08); }

.btnSec {
  border: 1px solid var(--line-2);
  padding: 13px 22px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 13px;
  color: var(--ink-0);
  transition: background 0.2s;
}

.btnSec:hover { background: var(--paper-1); }

.micro {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-3);
  letter-spacing: 0.05em;
}

.astrolabeWrap {
  display: grid;
  place-items: center;
  position: relative;
  width: 100%;
  max-width: 380px;
  margin-inline: auto;
  aspect-ratio: 1;
}

@media (min-width: 1024px) {
  .astrolabeWrap { margin-inline: 0 auto 0 0; justify-self: end; }
}

.astrolabeWrap svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 40px oklch(0.66 0.16 256 / 0.08));
}

.ringRotate {
  transform-origin: 190px 190px;
  animation: spinSlow 60s linear infinite;
}

@keyframes spinSlow {
  to { transform: rotate(360deg); }
}

.dotPulse { animation: pulse 2s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }
@keyframes pulse {
  0%, 100% { opacity: 0.85; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.15); }
}

.haloBreath { animation: breath 3s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }
@keyframes breath {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.75; }
}

.centerLabel {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--ink-2);
  text-transform: uppercase;
  pointer-events: none;
}

.centerLabel b {
  display: block;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 32px;
  letter-spacing: -0.03em;
  color: var(--danger);
  margin-top: 4px;
  text-shadow: 0 0 30px oklch(0.66 0.16 25 / 0.4);
}

@media (prefers-reduced-motion: reduce) {
  .ringRotate, .dotPulse, .haloBreath { animation: none; }
}
```

- [ ] **Step 2: Criar componente `hero-astrolabe.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";
import styles from "./hero-astrolabe.module.css";
import { lpDuration, lpEase } from "./lp-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0 },
};

export function HeroAstrolabe() {
  return (
    <section className={styles.heroRoot} aria-label="Hero">
      <div className={styles.grain} aria-hidden />
      <div className={styles.body}>
        <motion.div
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.08, delayChildren: 0.1 }}
        >
          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.eyebrow}
          >
            PARA TIMES B2B QUE PROSPECTAM EM ESCALA
          </motion.div>

          <motion.h1
            variants={fadeUp}
            transition={{ duration: lpDuration.slow, ease: lpEase }}
            className={styles.h1}
          >
            Pare de pagar SDR pra abrir LinkedIn.
          </motion.h1>

          <motion.p
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.sub}
          >
            SDR Machine acha o lead, lê o que existe sobre ele, prepara a abordagem e
            abre a conversa. Você define o canal e o material.
          </motion.p>

          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.ctas}
          >
            <a href="#agendar" className={styles.btnPri}>
              Agendar demo
            </a>
            <a href="#como-funciona" className={styles.btnSec}>
              Ver em ação ↓
            </a>
          </motion.div>

          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.micro}
          >
            500 leads/h · enriquecimento + abordagem prontos
          </motion.div>
        </motion.div>

        <motion.div
          className={styles.astrolabeWrap}
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: lpEase, delay: 0.4 }}
        >
          <Astrolabe />
          <div className={styles.centerLabel}>
            OPORTUNIDADE TOPO
            <b>87</b>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Astrolabe() {
  return (
    <svg viewBox="0 0 380 380" fill="none" aria-hidden>
      {/* Anel externo */}
      <circle cx="190" cy="190" r="180" stroke="var(--warn)" strokeWidth="0.5" opacity="0.35" />
      <circle cx="190" cy="190" r="178" stroke="var(--ink-2)" strokeOpacity="0.18" strokeWidth="1" />

      {/* Ticks cardeais + ordinais */}
      <g stroke="var(--ink-2)" strokeOpacity="0.4" strokeWidth="0.8">
        <line x1="190" y1="10" x2="190" y2="22" />
        <line x1="190" y1="358" x2="190" y2="370" />
        <line x1="10" y1="190" x2="22" y2="190" />
        <line x1="358" y1="190" x2="370" y2="190" />
      </g>
      <g stroke="var(--ink-2)" strokeOpacity="0.22" strokeWidth="0.8">
        <line x1="65" y1="65" x2="73" y2="73" />
        <line x1="307" y1="73" x2="315" y2="65" />
        <line x1="65" y1="315" x2="73" y2="307" />
        <line x1="307" y1="307" x2="315" y2="315" />
      </g>

      {/* Anéis intermediários */}
      <circle cx="190" cy="190" r="148" stroke="var(--ink-2)" strokeOpacity="0.14" strokeWidth="1" />
      <g className={styles.ringRotate}>
        <circle cx="190" cy="190" r="120" stroke="var(--warn)" strokeWidth="0.8" strokeDasharray="2 6" opacity="0.55" />
      </g>
      <circle cx="190" cy="190" r="92" stroke="var(--ink-2)" strokeOpacity="0.16" strokeWidth="1" />

      {/* Crosshair */}
      <line x1="190" y1="42" x2="190" y2="338" stroke="var(--ink-2)" strokeOpacity="0.06" strokeWidth="0.8" />
      <line x1="42" y1="190" x2="338" y2="190" stroke="var(--ink-2)" strokeOpacity="0.06" strokeWidth="0.8" />
      <line x1="80" y1="80" x2="300" y2="300" stroke="var(--ink-2)" strokeOpacity="0.04" strokeWidth="0.6" strokeDasharray="2 5" />
      <line x1="300" y1="80" x2="80" y2="300" stroke="var(--ink-2)" strokeOpacity="0.04" strokeWidth="0.6" strokeDasharray="2 5" />

      {/* Pontos plotados */}
      <g>
        <circle cx="265" cy="115" r="5" fill="var(--danger)" className={styles.dotPulse} />
        <circle cx="265" cy="115" r="11" fill="none" stroke="var(--danger)" strokeWidth="0.8" opacity="0.4" />
        <text x="278" y="113" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">87</text>

        <circle cx="295" cy="220" r="4.5" fill="var(--danger)" className={styles.dotPulse} />
        <text x="306" y="223" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">92</text>

        <circle cx="120" cy="265" r="4" fill="var(--warn)" />
        <text x="98" y="282" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">71</text>

        <circle cx="105" cy="125" r="3.5" fill="var(--ok)" />
        <text x="80" y="115" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-4)" letterSpacing="1">48</text>

        {/* Centro azul */}
        <circle cx="190" cy="190" r="6" fill="var(--accent)" />
        <circle cx="190" cy="190" r="14" fill="none" stroke="var(--accent)" strokeWidth="0.8" className={styles.haloBreath} />
      </g>
    </svg>
  );
}
```

- [ ] **Step 3: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/marketing/hero-astrolabe.tsx frontend/src/components/marketing/hero-astrolabe.module.css
git commit -m "feat(marketing): hero astrolábio SVG + copy 'Pare de pagar SDR'"
```

---

## Task 4: Marketing navbar refresh (sticky pós 80vh)

**Files:**
- Modify: `frontend/src/components/marketing/marketing-navbar.tsx`

- [ ] **Step 1: Reescrever navbar**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";

export function MarketingNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > window.innerHeight * 0.8);
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        backgroundColor: scrolled ? "color-mix(in oklch, var(--paper-0) 80%, transparent)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid var(--line-2)" : "1px solid transparent",
      }}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <nav className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[15px] font-semibold tracking-tight" style={{ color: "var(--ink-0)" }}>
            SDR Machine
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          <a href="#como-funciona" className="text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Como funciona
          </a>
          <a href="#pratica" className="text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Veja na prática
          </a>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/app" className="hidden sm:inline text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Login
          </Link>
          <a
            href="#agendar"
            className="text-sm font-medium rounded-md px-4 py-2 hover:opacity-90 transition-opacity"
            style={{ background: "var(--ink-0)", color: "var(--paper-0)" }}
          >
            Agendar demo
          </a>
        </div>
      </nav>
    </motion.header>
  );
}
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/marketing-navbar.tsx
git commit -m "feat(marketing): navbar sticky com fade-in pós 80vh"
```

---

## Task 5: Section 03 — O Problema (3 cards com count-up)

**Files:**
- Create: `frontend/src/components/marketing/problem-section.tsx`

- [ ] **Step 1: Criar componente**

```tsx
"use client";

import { motion } from "framer-motion";
import { useCountUp, useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

const CARDS = [
  { value: 8, suffix: "h", label: "ABAS · FERRAMENTAS", text: "40 abas, 12 ferramentas, 0 contexto." },
  { value: 1.2, suffix: "%", label: "RESPOSTA EM MENSAGEM GENÉRICA", text: "“Olá, vi que você é dono de…” — copy que ninguém lê." },
  { value: 0, suffix: "%", label: "CONTEXTO ANTES DA CONVERSA", text: "Seu SDR fala antes de saber o que dói. O cliente sente." },
];

export function ProblemSection() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>();

  return (
    <section className="relative py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div ref={ref} className="mx-auto max-w-5xl text-center">
        <motion.h2
          initial={{ opacity: 0, y: 18 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase }}
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.05, fontWeight: 480 }}
          className="font-sans mb-16"
        >
          Hoje você paga 8 horas de SDR
          <br />
          pra entregar 2.
        </motion.h2>

        <div className="grid md:grid-cols-3 gap-4">
          {CARDS.map((card, i) => (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 18 }}
              animate={visible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: lpDuration.base, ease: lpEase, delay: i * 0.06 }}
              className="rounded-lg p-7 text-left"
              style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
            >
              <ProblemNumber value={card.value} suffix={card.suffix} />
              <div
                className="font-mono mt-1 mb-3"
                style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
              >
                {card.label}
              </div>
              <p style={{ color: "var(--ink-2)", fontSize: "14px", lineHeight: 1.55 }}>
                {card.text}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemNumber({ value, suffix }: { value: number; suffix: string }) {
  const { ref, value: animated } = useCountUp(value, 800);
  const formatted = Number.isInteger(value) ? Math.round(animated).toString() : animated.toFixed(1);
  return (
    <span
      ref={ref}
      className="font-mono tabular-nums block"
      style={{ color: "var(--warn)", fontSize: "96px", fontWeight: 600, lineHeight: 0.9, letterSpacing: "-0.03em" }}
    >
      {formatted}
      {suffix}
    </span>
  );
}
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/problem-section.tsx
git commit -m "feat(marketing): section 'O Problema' com 3 cards e count-up"
```

---

## Task 6: Section 04 — Promessa em 4 atos

**Files:**
- Create: `frontend/src/components/marketing/promise-acts.tsx`
- Create: `frontend/src/components/marketing/promise-mockups/mockup-acha.tsx`
- Create: `frontend/src/components/marketing/promise-mockups/mockup-entende.tsx`
- Create: `frontend/src/components/marketing/promise-mockups/mockup-prepara.tsx`
- Create: `frontend/src/components/marketing/promise-mockups/mockup-abre.tsx`
- Create: `frontend/src/components/marketing/promise-mockups/index.ts`

- [ ] **Step 1: Criar `promise-acts.tsx`**

```tsx
"use client";

import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";
import { MockupAcha, MockupEntende, MockupPrepara, MockupAbre } from "./promise-mockups";

type Act = {
  num: string;
  verb: string;
  h3: string;
  sub: string;
  bullets: string[];
  Mockup: React.ComponentType;
};

const ACTS: Act[] = [
  {
    num: "01",
    verb: "ACHA",
    h3: "Onde seu cliente está. E quem é ele.",
    sub: "Pesquisa em Google Maps, Apollo e sua base. Encontra empresas que batem com seu ICP, deduplica, valida CNPJ e enriquece contatos.",
    bullets: ["Filtro nicho × cidade", "Deduplicação automática", "CNPJ + razão social validados"],
    Mockup: MockupAcha,
  },
  {
    num: "02",
    verb: "ENTENDE",
    h3: "Lê o site. Abre a stack. Entende a dor real.",
    sub: "Crawl do site, schema.org, tech stack, reviews do Google. Calcula um score 0-100 com 10+ sinais. Você sabe o que dói antes de falar.",
    bullets: ["10+ sinais (SSL, mobile, stack, reviews)", "Score 0-100 explicável", "Reasons em texto pronto"],
    Mockup: MockupEntende,
  },
  {
    num: "03",
    verb: "PREPARA",
    h3: "Material certo. Pra esse lead. Em segundos.",
    sub: "Gera o asset de abordagem que faz sentido pro lead — landing page personalizada, infográfico de diagnóstico, mockup. Tudo público, sem login, pronto pra enviar.",
    bullets: ["Templates conectados ao diagnóstico", "LP, infográfico ou mockup", "URL pública dedicada"],
    Mockup: MockupPrepara,
  },
  {
    num: "04",
    verb: "ABRE",
    h3: "Mensagem pronta. No canal certo. Em pt-BR humano.",
    sub: "Compõe abordagem inicial, follow-up de 48h e mensagem final. Link wa.me pré-preenchido. Tom configurável (formal, parceiro, direto).",
    bullets: ["3 cadências por lead", "WhatsApp, e-mail, ligação", "Tom configurável"],
    Mockup: MockupAbre,
  },
];

export function PromiseActs() {
  return (
    <section id="como-funciona" className="py-16" style={{ background: "var(--paper-0)" }}>
      {ACTS.map((act, i) => (
        <ActRow key={act.num} act={act} reverse={i % 2 === 1} />
      ))}
    </section>
  );
}

function ActRow({ act, reverse }: { act: Act; reverse: boolean }) {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.15);
  const Mockup = act.Mockup;
  const reverseClass = reverse ? "lg:[&>*:first-child]:order-2" : "";
  return (
    <div ref={ref} className="mx-auto max-w-6xl px-6 py-16 lg:py-24">
      <div className={`grid gap-10 lg:gap-16 items-center lg:grid-cols-2 ${reverseClass}`}>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase }}
        >
          <div
            className="font-mono mb-4 inline-flex items-center gap-2"
            style={{ color: "var(--warn)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
          >
            <span style={{ width: "16px", height: "1px", background: "var(--warn)" }} />
            {act.num} · {act.verb}
          </div>
          <h3
            className="font-sans mb-4"
            style={{ color: "var(--ink-0)", fontSize: "clamp(24px, 3.5vw, 36px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
          >
            {act.h3}
          </h3>
          <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, maxWidth: "480px", marginBottom: "24px" }}>
            {act.sub}
          </p>
          <ul className="space-y-2 font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>
            {act.bullets.map((b) => (
              <li key={b} className="flex items-start gap-2">
                <span style={{ color: "var(--warn)", marginTop: "2px" }}>·</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase, delay: 0.1 }}
        >
          <Mockup />
        </motion.div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Criar `promise-mockups/index.ts`**

```ts
export { MockupAcha } from "./mockup-acha";
export { MockupEntende } from "./mockup-entende";
export { MockupPrepara } from "./mockup-prepara";
export { MockupAbre } from "./mockup-abre";
```

- [ ] **Step 3: Criar `mockup-acha.tsx`**

```tsx
"use client";

const LEADS = [
  { name: "Padaria do Zé", meta: "Pinheiros · Padaria", score: 87, tone: "var(--danger)" },
  { name: "Auto Mec. Silva", meta: "Lapa · Mecânica", score: 92, tone: "var(--danger)" },
  { name: "Café Aurora", meta: "Vila Madalena · Cafeteria", score: 71, tone: "var(--warn)" },
  { name: "Studio Pilates Rê", meta: "Itaim · Pilates", score: 64, tone: "var(--warn)" },
  { name: "Pet Shop Bicho", meta: "Moema · Pet", score: 89, tone: "var(--danger)" },
];

export function MockupAcha() {
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
      <div
        className="px-4 py-3 flex items-center justify-between font-mono"
        style={{ borderBottom: "1px solid var(--line-2)", color: "var(--ink-3)", fontSize: "11px" }}
      >
        <span>5 LEADS · PADARIA × PINHEIROS</span>
        <span style={{ color: "var(--warn)" }}>FILTRO ATIVO</span>
      </div>
      <ul>
        {LEADS.map((l, idx) => (
          <li
            key={l.name}
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: idx === LEADS.length - 1 ? "none" : "1px solid var(--line-2)" }}
          >
            <div>
              <div style={{ color: "var(--ink-0)", fontSize: "14px", fontWeight: 500 }}>{l.name}</div>
              <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>{l.meta}</div>
            </div>
            <div className="font-mono tabular-nums" style={{ color: l.tone, fontSize: "14px", fontWeight: 600 }}>{l.score}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Criar `mockup-entende.tsx`**

```tsx
"use client";

const DIMS = [
  { label: "SSL", value: 0, hint: "ausente" },
  { label: "MOBILE", value: 15, hint: "quebrado" },
  { label: "STACK", value: 60, hint: "Wix '19" },
  { label: "REVIEWS", value: 88, hint: "4.6 ★" },
];

export function MockupEntende() {
  return (
    <div className="rounded-lg p-6" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
      <div className="flex items-baseline justify-between mb-1">
        <div style={{ color: "var(--ink-0)", fontSize: "14px", fontWeight: 500 }}>Padaria do Zé</div>
        <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>PINHEIROS · SP</div>
      </div>
      <div className="font-mono mb-4" style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
        DIAGNÓSTICO DE PRESENÇA DIGITAL
      </div>
      <div className="flex items-center gap-6 mb-6">
        <div
          className="font-mono tabular-nums"
          style={{ color: "var(--danger)", fontSize: "64px", fontWeight: 600, lineHeight: 0.9, letterSpacing: "-0.03em" }}
        >
          87
        </div>
        <div>
          <div className="font-mono mb-1" style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
            SCORE
          </div>
          <div style={{ color: "var(--danger)", fontSize: "12px", fontWeight: 500 }}>Aja agora</div>
        </div>
      </div>
      <div className="space-y-3">
        {DIMS.map((d) => (
          <div key={d.label}>
            <div className="flex justify-between font-mono mb-1" style={{ fontSize: "11px" }}>
              <span style={{ color: "var(--ink-3)" }}>{d.label}</span>
              <span style={{ color: "var(--ink-2)" }}>{d.hint}</span>
            </div>
            <div className="rounded-full overflow-hidden" style={{ height: "4px", background: "var(--paper-2)" }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${d.value}%`,
                  background: d.value < 30 ? "var(--danger)" : d.value < 70 ? "var(--warn)" : "var(--ok)",
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--line-2)" }}>
        <div className="font-mono mb-2" style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
          RAZÕES
        </div>
        <ul className="space-y-1" style={{ color: "var(--ink-2)", fontSize: "12px" }}>
          <li>· Site sem HTTPS</li>
          <li>· Stack desatualizado (Wix 2019)</li>
          <li>· Sem breakpoint mobile</li>
        </ul>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Criar `mockup-prepara.tsx`**

```tsx
"use client";

import { useMockupLoop } from "../lp-motion";

const ASSETS = [
  { kind: "Landing page", desc: "Hero + CTA + dor inline", color: "var(--accent)" },
  { kind: "Infográfico", desc: "Diagnóstico em 1 página A4", color: "var(--warn)" },
  { kind: "Mockup do site", desc: "Antes / depois lado a lado", color: "var(--danger)" },
];

export function MockupPrepara() {
  const active = useMockupLoop(ASSETS.length, 3500);
  return (
    <div className="grid grid-cols-3 gap-3">
      {ASSETS.map((a, i) => (
        <div
          key={a.kind}
          className="rounded-md p-3 flex flex-col justify-end transition-all"
          style={{
            aspectRatio: "3/4",
            background: "var(--paper-1)",
            border: `1px solid ${i === active ? a.color : "var(--line-2)"}`,
            boxShadow: i === active ? `0 0 0 2px color-mix(in oklch, ${a.color} 25%, transparent)` : "none",
            transform: i === active ? "translateY(-4px)" : "none",
          }}
        >
          <div
            className="flex-1 rounded mb-2"
            style={{
              background: i === active
                ? `linear-gradient(180deg, color-mix(in oklch, ${a.color} 18%, transparent), color-mix(in oklch, ${a.color} 4%, transparent))`
                : "var(--paper-2)",
            }}
          />
          <div style={{ color: "var(--ink-0)", fontSize: "12px", fontWeight: 500 }}>{a.kind}</div>
          <div className="font-mono leading-tight mt-1" style={{ color: "var(--ink-3)", fontSize: "10px" }}>{a.desc}</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Criar `mockup-abre.tsx`**

```tsx
"use client";

const MSGS = [
  { when: "INICIAL · DIA 0", body: "Oi Zé, vi que o site da padaria não abre direito no celular. Tenho um esboço de como ficaria — quer dar uma olhada antes de a gente conversar?" },
  { when: "FOLLOW-UP · DIA 2", body: "E aí Zé, só dando ping. O esboço tá em padaria-do-ze.sdrmachine.com — 5 minutinhos de leitura." },
  { when: "FECHAMENTO · DIA 5", body: "Zé, última tentativa. Se fizer sentido, marcar 15 min essa semana. Senão, sumo daqui." },
];

export function MockupAbre() {
  return (
    <div className="space-y-3">
      {MSGS.map((m) => (
        <div key={m.when} className="rounded-md p-4" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
          <div
            className="font-mono mb-2"
            style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
          >
            {m.when}
          </div>
          <p style={{ color: "var(--ink-1)", fontSize: "13px", lineHeight: 1.6 }}>{m.body}</p>
        </div>
      ))}
      <a
        href="#"
        onClick={(e) => e.preventDefault()}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md"
        style={{ background: "oklch(0.62 0.15 145)", color: "var(--paper-0)", fontSize: "12px", fontWeight: 500 }}
      >
        Abrir no WhatsApp →
      </a>
    </div>
  );
}
```

- [ ] **Step 7: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/marketing/promise-acts.tsx frontend/src/components/marketing/promise-mockups/
git commit -m "feat(marketing): promessa em 4 atos (acha · entende · prepara · abre)"
```

---

## Task 7: Section 05 — Veja na Prática (redesign)

**Files:**
- Modify: `frontend/src/components/marketing/practice-block.tsx`

- [ ] **Step 1: Verificar signatures dos componentes shared**

Antes de editar, leia:
- `frontend/src/components/shared/agent-chat.tsx`
- `frontend/src/components/shared/digital-blueprint.tsx`
- `frontend/src/components/shared/mission-control.tsx`

Confirme as props que cada um recebe (`data` prop ou outra estrutura). Mantenha a forma como o original `practice-block.tsx` os chama.

- [ ] **Step 2: Reescrever practice-block**

```tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentChat } from "@/components/shared/agent-chat";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { LP_CHAT_DATA, LP_BLUEPRINT_DATA, LP_MISSION_DATA } from "@/lib/practice-data";
import { lpDuration, lpEase } from "./lp-motion";

const TABS = [
  { key: "blueprint", label: "Diagnóstico" },
  { key: "chat", label: "Atendimento" },
  { key: "mission", label: "Mission Control" },
] as const;

type TabKey = typeof TABS[number]["key"];

export function PracticeBlock() {
  const [activeTab, setActiveTab] = useState<TabKey>("blueprint");

  return (
    <section id="pratica" className="relative py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div className="mx-auto max-w-5xl text-center mb-12">
        <div
          className="font-mono mb-4 inline-flex items-center gap-2"
          style={{ color: "var(--warn)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
        >
          <span style={{ width: "16px", height: "1px", background: "var(--warn)" }} />
          DEMONSTRAÇÃO
        </div>
        <h2
          className="font-sans mb-3"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Veja em prática. Sem rodar nada.
        </h2>
        <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, maxWidth: "560px", margin: "0 auto" }}>
          Escolha um aspecto do produto e veja o que sairia da máquina pra um lead real.
        </p>
      </div>

      <div className="mx-auto max-w-5xl">
        <div
          className="flex justify-center gap-1 mb-8 rounded-md p-1 w-fit mx-auto"
          style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
        >
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className="px-4 py-2 rounded transition-colors"
              style={{
                fontSize: "13px",
                fontWeight: 500,
                background: activeTab === t.key ? "var(--paper-3)" : "transparent",
                color: activeTab === t.key ? "var(--ink-0)" : "var(--ink-3)",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: lpDuration.fast, ease: lpEase }}
            className="rounded-lg p-6"
            style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
          >
            {activeTab === "chat" && <AgentChat data={LP_CHAT_DATA} />}
            {activeTab === "blueprint" && <DigitalBlueprint data={LP_BLUEPRINT_DATA} />}
            {activeTab === "mission" && <MissionControl data={LP_MISSION_DATA} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
```

**Se as props dos componentes shared forem diferentes** (ex.: `<AgentChat steps={...}>` em vez de `<AgentChat data={...}>`), ajuste no spot — não invente prop nova.

- [ ] **Step 3: Verificar visual**

Run: `cd frontend && npm run dev`
Abrir `http://localhost:3000/#pratica`. Trocar abas — transição suave, sem regressão visual interna nos componentes shared.

- [ ] **Step 4: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/marketing/practice-block.tsx
git commit -m "feat(marketing): redesign do practice-block no DS dark"
```

---

## Task 8: Section 06 — Stack que substitui

**Files:**
- Create: `frontend/src/components/marketing/stack-substitutes.tsx`

- [ ] **Step 1: Criar componente**

```tsx
"use client";

import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

const TOOLS = ["Apollo", "Lusha", "ChatGPT", "Mailshake", "Carrd"];

export function StackSubstitutes() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.2);
  return (
    <section ref={ref} className="py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div className="mx-auto max-w-4xl text-center">
        <h2
          className="font-sans mb-12"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Hoje, a mesma entrega
          <br />
          usa 5 ferramentas.
        </h2>

        <div className="flex flex-wrap justify-center gap-4 mb-10">
          {TOOLS.map((tool, i) => (
            <motion.div
              key={tool}
              initial={{ opacity: 0, y: 8 }}
              animate={visible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: lpDuration.base, ease: lpEase, delay: i * 0.08 }}
              className="relative rounded-md px-6 py-4"
              style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)", minWidth: "140px" }}
            >
              <div style={{ color: "var(--ink-3)", fontWeight: 500, filter: "grayscale(1)" }}>
                {tool}
              </div>
              <motion.div
                initial={{ scale: 1.4, opacity: 0 }}
                animate={visible ? { scale: 1, opacity: 1 } : {}}
                transition={{ duration: 0.3, ease: lpEase, delay: 0.4 + i * 0.08 }}
                className="absolute inset-0 grid place-items-center pointer-events-none"
              >
                <span
                  style={{ color: "var(--danger)", fontSize: "32px", fontWeight: 700, transform: "rotate(-8deg)" }}
                >
                  ✕
                </span>
              </motion.div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase, delay: 0.9 }}
          className="flex flex-col items-center gap-6"
        >
          <div style={{ color: "var(--ink-3)", fontSize: "24px" }}>↓</div>
          <div
            className="rounded-lg px-8 py-5"
            style={{
              border: "1px solid var(--line-3)",
              background: "var(--paper-1)",
              boxShadow: "0 0 40px oklch(0.66 0.16 256 / 0.15)",
            }}
          >
            <div className="font-sans tracking-tight" style={{ color: "var(--ink-0)", fontSize: "20px", fontWeight: 600 }}>SDR Machine</div>
          </div>
          <div
            className="font-mono mt-4"
            style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.05em" }}
          >
            + 8h/dia de SDR consolidando manualmente.
          </div>
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/stack-substitutes.tsx
git commit -m "feat(marketing): section 'Stack que substitui' com 5 logos riscadas"
```

---

## Task 9: Section 08 — CTA Calendly inline

**Files:**
- Create: `frontend/src/components/marketing/cta-calendly.tsx`

- [ ] **Step 1: Criar componente**

```tsx
"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

export function CtaCalendly() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.15);
  const calendlyUrl = process.env.NEXT_PUBLIC_CALENDLY_URL;

  useEffect(() => {
    if (!calendlyUrl) return;
    const script = document.createElement("script");
    script.src = "https://assets.calendly.com/assets/external/widget.js";
    script.async = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, [calendlyUrl]);

  return (
    <section
      id="agendar"
      ref={ref}
      className="py-24 px-6 relative overflow-hidden"
      style={{ background: "var(--paper-1)" }}
    >
      {/* Astrolábio reduzido como decoração */}
      <div className="absolute right-[-60px] top-1/2 -translate-y-1/2 w-[280px] h-[280px] opacity-20 pointer-events-none hidden lg:block">
        <svg viewBox="0 0 380 380" fill="none">
          <circle cx="190" cy="190" r="180" stroke="var(--warn)" strokeWidth="0.5" opacity="0.5" />
          <circle cx="190" cy="190" r="148" stroke="var(--ink-2)" strokeOpacity="0.3" strokeWidth="1" />
          <circle cx="190" cy="190" r="120" stroke="var(--warn)" strokeWidth="0.8" strokeDasharray="2 6" opacity="0.7" />
          <circle cx="190" cy="190" r="92" stroke="var(--ink-2)" strokeOpacity="0.3" strokeWidth="1" />
          <circle cx="190" cy="190" r="6" fill="var(--accent)" />
        </svg>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={visible ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: lpDuration.slow, ease: lpEase }}
        className="relative mx-auto max-w-3xl text-center"
      >
        <h2
          className="font-sans mb-4"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Pronto pra parar de pagar
          <br />
          SDR pra abrir LinkedIn?
        </h2>
        <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, marginBottom: "40px" }}>
          15 min de demo. Roda na sua base. Sem compromisso.
        </p>

        {calendlyUrl ? (
          <div
            className="calendly-inline-widget rounded-lg overflow-hidden"
            data-url={calendlyUrl}
            style={{ minWidth: "320px", height: "640px", border: "1px solid var(--line-2)", background: "var(--paper-0)" }}
          />
        ) : (
          <div
            className="rounded-lg p-12"
            style={{ border: "1px solid var(--line-2)", background: "var(--paper-0)", color: "var(--ink-3)" }}
          >
            Calendly ainda não configurado. Defina <code className="font-mono">NEXT_PUBLIC_CALENDLY_URL</code>.
          </div>
        )}

        <div
          className="font-mono mt-6"
          style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.05em" }}
        >
          Resposta em &lt;2h
        </div>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/cta-calendly.tsx
git commit -m "feat(marketing): CTA final com Calendly embed inline"
```

---

## Task 10: Footer redesign

**Files:**
- Modify: `frontend/src/components/marketing/marketing-footer.tsx`

- [ ] **Step 1: Reescrever footer**

```tsx
"use client";

import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="py-16 px-6" style={{ background: "var(--paper-0)", borderTop: "1px solid var(--line-2)" }}>
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 md:grid-cols-[2fr_3fr]">
          <div>
            <Link href="/" className="font-semibold tracking-tight" style={{ color: "var(--ink-0)", fontSize: "15px" }}>
              SDR Machine
            </Link>
            <p style={{ color: "var(--ink-3)", fontSize: "14px", marginTop: "8px" }}>Instrumento de prospecção.</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8">
            <FooterColumn title="Produto" links={[
              { label: "Como funciona", href: "#como-funciona" },
              { label: "Veja em prática", href: "#pratica" },
              { label: "Agendar demo", href: "#agendar" },
            ]} />
            <FooterColumn title="Empresa" links={[
              { label: "Sollertis", href: "https://sollertis.com.br", external: true },
              { label: "Contato", href: "mailto:contato@sollertis.com.br" },
            ]} />
            <FooterColumn title="Legal" links={[
              { label: "Privacidade", href: "/privacidade" },
              { label: "Termos", href: "/termos" },
            ]} />
          </div>
        </div>

        <div className="flex items-center justify-between mt-12 pt-6" style={{ borderTop: "1px solid var(--line-2)" }}>
          <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>© 2026 Sollertis</div>
          <a
            href="https://www.linkedin.com/company/sollertis"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--ink-3)" }}
          >
            LinkedIn
          </a>
        </div>
      </div>
    </footer>
  );
}

type Link = { label: string; href: string; external?: boolean };

function FooterColumn({ title, links }: { title: string; links: Link[] }) {
  return (
    <div>
      <div
        className="font-mono mb-3"
        style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
      >
        {title}
      </div>
      <ul className="space-y-2">
        {links.map((l) => (
          <li key={l.label}>
            <a
              href={l.href}
              target={l.external ? "_blank" : undefined}
              rel={l.external ? "noreferrer" : undefined}
              style={{ color: "var(--ink-2)", fontSize: "14px" }}
            >
              {l.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/marketing/marketing-footer.tsx
git commit -m "feat(marketing): footer redesenhado no DS Instrumento"
```

---

## Task 11: Page wiring — `(marketing)/page.tsx`

**Files:**
- Modify: `frontend/src/app/(marketing)/page.tsx`

- [ ] **Step 1: Reescrever page**

```tsx
import { HeroAstrolabe } from "@/components/marketing/hero-astrolabe";
import { ProblemSection } from "@/components/marketing/problem-section";
import { PromiseActs } from "@/components/marketing/promise-acts";
import { PracticeBlock } from "@/components/marketing/practice-block";
import { StackSubstitutes } from "@/components/marketing/stack-substitutes";
import { CtaCalendly } from "@/components/marketing/cta-calendly";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function LandingPage() {
  return (
    <main>
      <HeroAstrolabe />

      {/* SLOT: Trust strip (logos clientes) — ativar quando tiver cases */}
      {/* <TrustStrip /> */}

      <ProblemSection />
      <PromiseActs />
      <PracticeBlock />
      <StackSubstitutes />

      {/* SLOT: Casos / Números — ativar quando tiver quote + métricas */}
      {/* <CasesNumbers /> */}

      <CtaCalendly />
      <MarketingFooter />
    </main>
  );
}
```

- [ ] **Step 2: Verificar página inteira no browser**

Run: `cd frontend && npm run dev`
Abrir `http://localhost:3000/`. Validar:
1. Hero astrolábio dark + copy correta + CTAs
2. Section "Hoje você paga 8 horas..." com 3 cards e count-up
3. 4 sub-sections de "Promessa em 4 atos" em zigzag
4. Veja na prática com 3 abas funcionais
5. Stack que substitui com 5 logos cinza + X carimbando
6. CTA Calendly (placeholder se sem env)
7. Footer

Mobile (375px via DevTools): tudo stacka corretamente.

- [ ] **Step 3: Lint check**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(marketing\)/page.tsx
git commit -m "feat(marketing): wire da nova sequência de sections"
```

---

## Task 12: Limpeza — remover componentes substituídos

**Files:**
- Delete: `frontend/src/components/marketing/hero-section.tsx`
- Delete: `frontend/src/components/marketing/before-after.tsx`
- Delete: `frontend/src/components/marketing/features-grid.tsx`
- Delete: `frontend/src/components/marketing/cta-section.tsx`
- Delete: `frontend/src/components/marketing/pipeline-section.tsx`

- [ ] **Step 1: Confirmar não-uso**

Run:
```bash
cd frontend && grep -r "hero-section\|before-after\|features-grid\|cta-section\|pipeline-section" src/ --include="*.tsx" --include="*.ts"
```
Expected: zero matches fora dos próprios arquivos.

- [ ] **Step 2: Verificar uso da Remotion hero-composition**

Run:
```bash
cd frontend && grep -rn "hero-composition\|particle-background\|pipeline-animation" src/ --include="*.tsx" --include="*.ts"
```
Se houver matches em arquivos NÃO-Remotion, MANTENHA os Remotion files (não delete).
Se único uso for entre os próprios componentes Remotion, pode deletá-los também — porém limpeza de deps `@remotion/*` em `package.json` está fora deste plan; deixar pra PR separado.

- [ ] **Step 3: Deletar os 5 componentes substituídos**

```bash
cd frontend
rm src/components/marketing/hero-section.tsx
rm src/components/marketing/before-after.tsx
rm src/components/marketing/features-grid.tsx
rm src/components/marketing/cta-section.tsx
rm src/components/marketing/pipeline-section.tsx
```

- [ ] **Step 4: Build check**

Run: `cd frontend && npm run build`
Expected: build sucede sem erros de import.

Se falhar, revise o erro, identifique import remanescente e corrija.

- [ ] **Step 5: Commit**

```bash
git add -u frontend/src/components/marketing/
git commit -m "chore(marketing): remover componentes da LP antiga"
```

---

## Task 13: Verificação final

**Files:** —

- [ ] **Step 1: Lint completo**

Run: `cd frontend && npm run lint`
Expected: zero errors.

- [ ] **Step 2: Build de produção**

Run: `cd frontend && npm run build`
Expected: build sucede.

- [ ] **Step 3: Smoke visual desktop (1280px)**

Run: `cd frontend && npm run dev`
Abrir `http://localhost:3000/` em janela 1280px+:
1. Hero astrolábio + copy + CTAs visíveis acima da dobra
2. Scroll: navbar fica sticky com fundo após ~80vh
3. "Problema": 3 cards lado a lado com count-up
4. "Promessa em 4 atos": zigzag com mockups visíveis
5. "Veja na prática": 3 abas funcionais
6. "Stack que substitui": logos cinza + X carimbando
7. "CTA Calendly": embed renderiza (ou placeholder)
8. Footer

- [ ] **Step 4: Smoke visual mobile (375px)**

DevTools → device toolbar 375×812:
1. Hero stacka vertical, astrolábio cabe sem cortar
2. Cards do "Problema" stackam (1 coluna)
3. "Promessa": cada ato vira coluna única (mockup primeiro top-to-bottom)
4. Stack substitui: logos quebram em wrap
5. Calendly embed responsive
6. Footer 2 colunas + bloco logo separado

- [ ] **Step 5: prefers-reduced-motion**

DevTools → Rendering → "Emulate CSS media feature prefers-reduced-motion" → reduce. Recarregar:
- Anel astrolábio NÃO gira
- Pontos NÃO pulsam
- Halo central NÃO respira
- Sections aparecem sem translate
- Count-up vai direto pro valor final

- [ ] **Step 6: Push da branch**

```bash
git push -u origin feat/marketing-lp-redesign
```

- [ ] **Step 7: Abrir PR**

```bash
gh pr create --title "feat(marketing): redesign da LP com DS Instrumento" --body "$(cat <<'EOF'
## Summary

- Hero novo (astrolábio SVG dark) substitui Remotion + copy "Pare de pagar SDR pra abrir LinkedIn"
- Promessa em 4 atos (acha · entende · prepara · abre) substitui FeaturesGrid + BeforeAfter
- Stack que substitui (5 logos riscadas) é nova section
- CTA final com Calendly embed inline
- LP escopa dark theme via classe local (não afeta toggle do app)
- Asset-agnostic: copy não menciona LP especificamente

## Test plan

- [ ] Smoke visual desktop (1280px) — todas as sections renderizam
- [ ] Smoke visual mobile (375px) — stack vertical correto
- [ ] prefers-reduced-motion desativa rotação/pulso/translate
- [ ] Calendly embed funciona com NEXT_PUBLIC_CALENDLY_URL
- [ ] `npm run build` sucede
- [ ] `npm run lint` sem erros

## Spec

`docs/superpowers/specs/2026-05-04-marketing-lp-redesign-design.md`
EOF
)"
```

---

## Self-review

**Spec coverage:**
- Hero (B1 dark astrolábio) → Task 3 ✓
- Trust strip skipped → Task 11 (slot comentado) ✓
- Problema → Task 5 ✓
- Promessa em 4 atos → Task 6 ✓
- Veja na Prática → Task 7 ✓
- Stack que substitui → Task 8 ✓
- Casos skipped → Task 11 (slot comentado) ✓
- CTA Calendly → Task 9 ✓
- Footer → Task 10 ✓
- Tema dark escopado → Task 1 ✓
- Env var Calendly → Task 1 ✓
- Motion system → Task 2 ✓
- Sticky navbar pós 80vh → Task 4 ✓
- 5 arquivos antigos removidos → Task 12 ✓
- Critérios de aceitação (build, lint, mobile, reduced-motion) → Task 13 ✓

**Sem placeholders.** Todo step tem código completo ou comando exato.

**Type/naming consistency:**
- Hooks `useFadeUpOnView`, `useCountUp`, `useMockupLoop`, `lpEase`, `lpDuration` — usados consistente nas Tasks 5, 6, 7, 8, 9.
- Mockups `MockupAcha`/`MockupEntende`/`MockupPrepara`/`MockupAbre` batem entre arquivo e index.
- Tokens DS via `var(--paper-0)`, `var(--ink-0)`, `var(--warn)`, `var(--danger)`, `var(--ok)`, `var(--accent)`, `var(--line-2)`, `var(--line-3)` consistentes em todas as tasks.

**Riscos identificados:**
- Task 7 depende dos componentes existentes em `shared/`. Step 1 obriga verificar signatures antes.
- Task 12 protege contra remover Remotion sem checar uso.
- Task 1 evita `dangerouslySetInnerHTML` usando classe CSS escopada — sincronia com `[data-theme="dark"]` precisa ser mantida manual no futuro (comentado no código).
