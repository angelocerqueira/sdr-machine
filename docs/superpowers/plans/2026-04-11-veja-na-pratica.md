# "Veja na Pratica" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive "Veja na Pratica" block to the marketing LP with 3 tabs: Chat Agentico, Blueprint Digital, Mission Control.

**Architecture:** 3 shared components in `components/shared/` (reusable between LP and app), 1 LP-specific wrapper in `components/marketing/`, mock data constants. All frontend, no backend changes.

**Tech Stack:** React 19, TypeScript, Framer Motion (already installed), SVG for radar chart, Tailwind CSS 4

**Spec:** `docs/superpowers/specs/2026-04-11-veja-na-pratica-design.md`

---

### Task 1: Types and mock data

**Files:**
- Create: `frontend/src/lib/practice-types.ts`
- Create: `frontend/src/lib/practice-data.ts`

- [ ] **Step 1: Create shared types**

Create `frontend/src/lib/practice-types.ts`:

```typescript
export interface ChatMessage {
  role: "bot" | "user";
  text: string;
}

export interface AgentChatData {
  businessName: string;
  niche: string;
  messages: ChatMessage[];
  quickActions: string[];
  responses: Record<string, ChatMessage[]>;
}

export interface GapBlock {
  severity: "critico" | "gap" | "fraco";
  problem: string;
  detail: string;
  solution: string;
  solutionDetail: string;
}

export interface BlueprintData {
  radarScores: {
    seo: number;
    performance: number;
    mobile: number;
    conteudo: number;
    seguranca: number;
    presenca: number;
  };
  maturityScore: number;
  gaps: GapBlock[];
}

export interface AgentPerformance {
  name: string;
  successRate: number;
  calls: number;
  cost: string;
}

export interface ActivityEvent {
  type: "lead" | "lp" | "resposta" | "outreach";
  title: string;
  detail: string;
  time: string;
}

export interface Integration {
  name: string;
  status: "connected" | "pending";
}

export interface MissionControlData {
  pipeline: {
    leadsCaptados: number;
    outreachEnviado: number;
    respostas: number;
    reunioes: number;
  };
  aiMetrics: {
    custoPorLead: string;
    roiIA: string;
    leadTimeMedio: string;
    taxaSucessoAgentes: string;
  };
  tokensSummary: {
    tokensConsumed: string;
    totalCost: string;
    revenueAttributed: string;
  };
  agents: AgentPerformance[];
  feed: ActivityEvent[];
  integrations: Integration[];
}
```

- [ ] **Step 2: Create mock data for LP**

Create `frontend/src/lib/practice-data.ts`:

```typescript
import type { AgentChatData, BlueprintData, MissionControlData } from "./practice-types";

export const LP_CHAT_DATA: AgentChatData = {
  businessName: "Escritorio Silva & Associados",
  niche: "Escritorio de Advocacia",
  messages: [
    { role: "bot", text: "Boa tarde. Sou o assistente digital do escritorio Silva & Associados. Em que posso ajudar?" },
    { role: "user", text: "Preciso de orientacao sobre um processo de divorcio. Quanto tempo leva em media?" },
    { role: "bot", text: "O prazo de um divorcio consensual costuma variar entre 30 a 90 dias. Se for litigioso, pode levar de 1 a 3 anos dependendo da complexidade.\n\nO Dr. Silva atende ambas as modalidades. Posso verificar a agenda e reservar um horario para uma consulta inicial?" },
  ],
  quickActions: ["Agendar consulta", "Quais documentos preciso?", "Valores e honorarios", "Areas de atuacao"],
  responses: {
    "Agendar consulta": [
      { role: "bot", text: "Temos horarios disponiveis na proxima terca (14h ou 16h) e quinta (10h). A consulta inicial e de 45 minutos. Qual horario funciona melhor?" },
    ],
    "Quais documentos preciso?": [
      { role: "bot", text: "Para divorcio consensual: RG, CPF, certidao de casamento atualizada, pacto antenupcial (se houver) e acordo sobre partilha de bens. Nosso escritorio auxilia na organizacao de toda a documentacao." },
    ],
    "Valores e honorarios": [
      { role: "bot", text: "Os honorarios variam conforme a complexidade. A consulta inicial e R$350 e inclui analise completa do caso com parecer do Dr. Silva. Posso agendar?" },
    ],
    "Areas de atuacao": [
      { role: "bot", text: "O escritorio atua em Direito de Familia, Direito Civil, Direito do Consumidor e Direito Imobiliario. Para cada area temos especialistas dedicados." },
    ],
  },
};

export const LP_BLUEPRINT_DATA: BlueprintData = {
  radarScores: { seo: 25, performance: 35, mobile: 70, conteudo: 55, seguranca: 15, presenca: 20 },
  maturityScore: 32,
  gaps: [
    { severity: "critico", problem: "Site sem SSL", detail: "Google marca 'Nao seguro'", solution: "LP profissional", solutionDetail: "SSL + mobile + SEO" },
    { severity: "critico", problem: "Sem atendimento digital", detail: "Leads perdidos fora do horario", solution: "Chat agentico 24/7", solutionDetail: "Atende, qualifica, agenda" },
    { severity: "fraco", problem: "Sem estrategia de outreach", detail: "Depende de indicacao", solution: "Outreach automatizado", solutionDetail: "WhatsApp + follow-up" },
    { severity: "fraco", problem: "Site lento e nao responsivo", detail: "PageSpeed 23/100", solution: "LP otimizada", solutionDetail: "95+ PageSpeed, mobile-first" },
  ],
};

export const LP_MISSION_DATA: MissionControlData = {
  pipeline: { leadsCaptados: 1247, outreachEnviado: 342, respostas: 67, reunioes: 23 },
  aiMetrics: { custoPorLead: "R$0.42", roiIA: "47x", leadTimeMedio: "3.2min", taxaSucessoAgentes: "94.2%" },
  tokensSummary: { tokensConsumed: "2.4M", totalCost: "R$523", revenueAttributed: "R$24.700" },
  agents: [
    { name: "Enrichment Agent", successRate: 96.1, calls: 840, cost: "R$187" },
    { name: "LP Generator", successRate: 92.8, calls: 412, cost: "R$264" },
    { name: "Outreach Agent", successRate: 88.5, calls: 342, cost: "R$72" },
  ],
  feed: [
    { type: "lead", title: "Lead qualificado", detail: "Clinica Dr. Santos — Score: 91", time: "2min" },
    { type: "lp", title: "LP gerada", detail: "Padaria Dona Maria — 1.2k tokens", time: "8min" },
    { type: "resposta", title: "Resposta recebida", detail: "Auto Mecanica Silva — 'Vamos conversar'", time: "15min" },
    { type: "outreach", title: "Outreach enviado", detail: "12 leads batch — follow-up 48h", time: "32min" },
  ],
  integrations: [
    { name: "WhatsApp", status: "connected" },
    { name: "Analytics", status: "connected" },
    { name: "Claude IA", status: "connected" },
    { name: "CRM", status: "pending" },
  ],
};
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/practice-types.ts frontend/src/lib/practice-data.ts
git commit -m "feat: add types and mock data for Veja na Pratica block"
```

---

### Task 2: Agent Chat component

The most complex component. Typewriter effect, waveform processing indicator, quick actions with pre-programmed responses.

**Files:**
- Create: `frontend/src/components/shared/agent-chat.tsx`

- [ ] **Step 1: Create the Agent Chat component**

Create `frontend/src/components/shared/agent-chat.tsx`. This component implements:

- Typewriter character-by-character animation for bot messages (30ms/char)
- Waveform bars processing indicator between bot messages (1.5s duration)
- Quick action pills that trigger pre-programmed responses
- Avatar with gradient + pulse ring animation
- Metadata line under bot messages (response time, source)
- Badge at bottom showing niche context

Key implementation details:
- Use `useState` for displayed messages, typing state, used actions
- Use `useEffect` with `setTimeout` chain for typewriter sequencing
- Use `useCallback` for quick action handler
- Waveform uses CSS animation on 7 bars with varying heights
- Quick actions disable after use (track in `Set<string>`)
- Component accepts `AgentChatData` prop — LP passes mock, app passes real data

The full component should be approximately 250-300 lines covering:
1. TypewriterText inner component (renders text char by char)
2. WaveformIndicator inner component (7 animated bars + "processando" label)
3. AvatarBubble inner component (gradient circle + pulse ring via CSS)
4. Main AgentChat component with message sequencing logic
5. Quick actions footer with click handlers

Follow the styling patterns from existing marketing components: Tailwind utilities, CSS custom properties (`text-accent`, `bg-surface-raised`, `border-border`, etc.), `font-[family-name:var(--font-mono)]` for labels.

Implement a `useTypewriter` hook or inline effect that:
1. On mount (or tab activation via `active` prop), starts the initial message sequence
2. Each bot message: show waveform 1.5s -> typewriter the text at 30ms/char
3. Each user message: appear instantly
4. After all initial messages, show quick actions
5. On quick action click: add user message instantly, show waveform 1.5s, typewriter bot response

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/shared/agent-chat.tsx
git commit -m "feat: add Agent Chat component with typewriter and quick actions"
```

---

### Task 3: Digital Blueprint component

Radar chart (SVG) + gap map side by side.

**Files:**
- Create: `frontend/src/components/shared/digital-blueprint.tsx`

- [ ] **Step 1: Create the Digital Blueprint component**

Create `frontend/src/components/shared/digital-blueprint.tsx`. This component implements:

**Radar Chart (left panel, 40% width):**
- SVG viewBox 200x200 with 6-axis hexagonal grid
- 3 concentric grid rings (stroke only, subtle)
- 6 axis lines from center to vertices
- Ideal shape: dashed green polygon at outer ring
- Current shape: solid red polygon at actual values (animated from 0 on view)
- Gap areas: semi-transparent red fill between ideal and current where gaps exist
- Vertex dots colored by value: green (>=70), yellow (40-69), red (<40)
- Labels at each vertex (SEO, Performance, Mobile, Conteudo, Seguranca, Presenca)
- Legend: dashed green = Ideal, solid red = Atual
- Score display: "{maturityScore}/100 Maturidade Digital"

Radar polygon calculation: convert each score (0-100) to a point on the hexagon. Use `polarToCartesian(centerX, centerY, radius * score/100, angle)` for each axis at 60-degree intervals.

Use Framer Motion `useInView` + `motion.polygon` to animate the current shape from center (all scores 0) to actual values on scroll.

**Gap Map (right panel, 60% width):**
- Vertical list of gap blocks, each showing:
  - Left card: severity badge (Critico/Gap/Fraco) + problem + detail
  - Arrow indicator (->)
  - Right card: "Solucao IA" badge + solution + solutionDetail
- Severity colors: critico=#f87171, gap=#f87171 lighter, fraco=#fbbf24
- Solution cards always green (#34d399)
- Connectors between blocks (vertical line)
- Framer Motion stagger animation: each block fades up with delay

Component accepts `BlueprintData` prop.

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/shared/digital-blueprint.tsx
git commit -m "feat: add Digital Blueprint component with radar chart and gap map"
```

---

### Task 4: Mission Control component

Dashboard with KPIs, activity feed, pipeline funnel, AI agent metrics.

**Files:**
- Create: `frontend/src/components/shared/mission-control.tsx`

- [ ] **Step 1: Create the Mission Control component**

Create `frontend/src/components/shared/mission-control.tsx`. This component implements:

**Status bar:** Green dot + "Sistema Operando" + uptime + last sync. Full-width rounded container with accent border.

**KPI Row 1 — Pipeline (4 cards, green accent):**
- Leads captados (with +18% variation)
- Outreach enviado (with 89% delivery rate)
- Respostas (with 19.6% rate)
- Reunioes (with 6.7% conversion) — accent border highlight

**KPI Row 2 — AI Metrics (4 cards, blue accent #60a5fa):**
- Custo por lead
- ROI da IA
- Lead time medio
- Taxa sucesso agentes

Use Framer Motion `useInView` for counter animation on KPI values. Animate from 0 to target value over 1.5s with easing.

**3-column grid:**

Left column — Activity Feed:
- Event cards with colored left border by type:
  - lead: #34d399
  - lp: #60a5fa
  - resposta: #fbbf24
  - outreach: rgba(52,211,153,0.4)
- Each card: bold colored title + detail text + relative time
- Framer Motion stagger entrance

Center column — Pipeline Funnel:
- 4 horizontal bars with labels and counts (Captados -> Analisados -> Outreach -> Fechados)
- Each bar proportional width relative to max (captados = 100%)
- Gradient fill green with decreasing opacity
- Bottom section: Integrations as small pills with colored dots (green=connected, yellow=pending)

Right column — Agent Performance (blue theme):
- Card per agent: name, success rate %, progress bar, calls count, cost
- Progress bar color: green (>=90%), yellow (80-89%), red (<80%)
- Token summary box at bottom: tokens consumed, total cost, revenue attributed
- Revenue line highlighted in green

Component accepts `MissionControlData` prop.

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/shared/mission-control.tsx
git commit -m "feat: add Mission Control dashboard component"
```

---

### Task 5: Practice Block wrapper + wire into LP

The tab container and LP page integration.

**Files:**
- Create: `frontend/src/components/marketing/practice-block.tsx`
- Modify: `frontend/src/app/(marketing)/page.tsx`

- [ ] **Step 1: Create the Practice Block wrapper**

Create `frontend/src/components/marketing/practice-block.tsx`:

```tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentChat } from "@/components/shared/agent-chat";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { LP_CHAT_DATA, LP_BLUEPRINT_DATA, LP_MISSION_DATA } from "@/lib/practice-data";

const TABS = [
  { key: "chat", label: "Atendimento IA" },
  { key: "blueprint", label: "Blueprint Digital" },
  { key: "mission", label: "Mission Control" },
] as const;

type TabKey = typeof TABS[number]["key"];

export function PracticeBlock() {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full opacity-100 pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(52,211,153,0.03) 0%, transparent 70%)" }}
      />

      {/* Header */}
      <div className="text-center mb-8 relative">
        <motion.p
          className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Veja na Pratica
        </motion.p>
        <motion.h2
          className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Seus clientes atendidos por IA. 24/7.
        </motion.h2>
        <motion.p
          className="text-text-secondary text-sm max-w-md mx-auto"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
        >
          Explore cada aspecto da inteligencia que vamos aplicar no seu negocio.
        </motion.p>
      </div>

      {/* Tabs */}
      <div className="flex justify-center gap-1 mb-8">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-5 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-200 ${
              activeTab === tab.key
                ? "bg-accent/10 border border-accent/30 text-accent"
                : "bg-white/[0.03] border border-white/[0.08] text-text-muted hover:text-text-secondary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === "chat" && <AgentChat data={LP_CHAT_DATA} />}
          {activeTab === "blueprint" && <DigitalBlueprint data={LP_BLUEPRINT_DATA} />}
          {activeTab === "mission" && <MissionControl data={LP_MISSION_DATA} />}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
```

- [ ] **Step 2: Wire into LP page**

Update `frontend/src/app/(marketing)/page.tsx`:

```tsx
import { HeroSection } from "@/components/marketing/hero-section";
import { BeforeAfter } from "@/components/marketing/before-after";
import { PipelineSection } from "@/components/marketing/pipeline-section";
import { PracticeBlock } from "@/components/marketing/practice-block";
import { FeaturesGrid } from "@/components/marketing/features-grid";
import { CTASection } from "@/components/marketing/cta-section";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function LandingPage() {
  return (
    <main>
      <HeroSection />
      <BeforeAfter />
      <PipelineSection />
      <PracticeBlock />
      <FeaturesGrid />
      <CTASection />
      <MarketingFooter />
    </main>
  );
}
```

- [ ] **Step 3: Verify build + lint**

```bash
cd frontend && npm run build && npm run lint
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/marketing/practice-block.tsx frontend/src/app/\(marketing\)/page.tsx
git commit -m "feat: add Practice Block wrapper with tabs and wire into LP"
```

---

### Task 6: Visual QA and polish

- [ ] **Step 1: Start dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Verify in browser**

Check `http://localhost:3000`:
- Scroll to "Veja na Pratica" block (after Pipeline, before Features Grid)
- Click each tab: Chat, Blueprint, Mission Control
- Chat: typewriter plays on tab activation, quick actions work
- Blueprint: radar animates on scroll, gap blocks stagger in
- Mission Control: KPI counters animate, feed staggers, funnel bars grow
- Test responsive: 375px, 768px, 1024px (60% max-width should adapt)

- [ ] **Step 3: Fix any issues found**

Address spacing, overflow, animation timing, or responsive issues.

- [ ] **Step 4: Final build + lint**

```bash
cd frontend && npm run build && npm run lint
```

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A frontend/src/
git commit -m "fix: polish Veja na Pratica block"
```
