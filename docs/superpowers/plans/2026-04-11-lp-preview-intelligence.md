# LP Preview Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the public LP preview page (`/lp/[id]`) with a floating chat widget, blueprint digital, and mission control — all fed by real enrichment data from the lead.

**Architecture:** Reuse the 3 shared components from PR #39 (agent-chat, digital-blueprint, mission-control). Create data transformer functions that convert a `Lead` object into the props each component expects. Add a floating chat widget wrapper and niche-specific chat templates. Modify the LP preview page to render everything together.

**Tech Stack:** React 19, TypeScript, Framer Motion (already installed), existing shared components

**Spec:** `docs/superpowers/specs/2026-04-11-lp-preview-intelligence-design.md`

---

### Task 1: Chat templates by niche

**Files:**
- Create: `frontend/src/lib/chat-templates.ts`

- [ ] **Step 1: Create chat templates file**

Create `frontend/src/lib/chat-templates.ts` with 6 niche templates + 1 generic fallback. Each template has pre-written messages and quick action responses contextualized to the niche. All messages use `{businessName}` placeholder that gets replaced at runtime.

The file should export:

```typescript
import type { ChatMessage, AgentChatData } from "./practice-types";

interface NicheTemplate {
  niche: string;
  messages: ChatMessage[];
  quickActions: string[];
  responses: Record<string, ChatMessage[]>;
}
```

**6 niche templates** (match via `lead.nicho?.toLowerCase().includes(template.niche)`):

1. **advocacia** — client asking about legal process, scheduling, documents, fees
2. **odonto/dentista** — patient asking about treatment, pain, scheduling, insurance
3. **restaurante** — customer asking about menu, reservation, delivery, hours
4. **academia** — prospect asking about plans, trial, schedule, trainers
5. **clinica/medic** — patient asking about appointments, exams, insurance coverage
6. **contabil** — entrepreneur asking about company registration, taxes, obligations

**Generic fallback** — uses `{businessName}` and `{niche}` placeholders, focuses on universal topics: services, scheduling, pricing, contact.

**Export function:**

```typescript
export function buildChatDataForLead(lead: { nome: string; nicho: string | null }): AgentChatData {
  const nicheKey = lead.nicho?.toLowerCase() || "";
  const template = NICHE_TEMPLATES.find(t => nicheKey.includes(t.niche)) || GENERIC_TEMPLATE;

  const replacePlaceholders = (text: string): string =>
    text.replace(/\{businessName\}/g, lead.nome).replace(/\{niche\}/g, lead.nicho || "empresa");

  const replaceInMessages = (msgs: ChatMessage[]): ChatMessage[] =>
    msgs.map(m => ({ ...m, text: replacePlaceholders(m.text) }));

  const replaceInResponses = (resps: Record<string, ChatMessage[]>): Record<string, ChatMessage[]> => {
    const result: Record<string, ChatMessage[]> = {};
    for (const [key, msgs] of Object.entries(resps)) {
      result[key] = replaceInMessages(msgs);
    }
    return result;
  };

  return {
    businessName: lead.nome,
    niche: lead.nicho || "Empresa",
    messages: replaceInMessages(template.messages),
    quickActions: [...template.quickActions],
    responses: replaceInResponses(template.responses),
  };
}
```

Each niche template should have:
- 3 initial messages (bot greeting, user question, bot detailed response)
- 4 quick actions relevant to the niche
- 4 response entries (one per quick action), each with 1 bot message

All bot messages use professional/specialist tone. No emojis.

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/chat-templates.ts
git commit -m "feat: add niche-specific chat templates for LP preview"
```

---

### Task 2: Lead to practice data transformers

**Files:**
- Create: `frontend/src/lib/lead-to-practice.ts`

- [ ] **Step 1: Create data transformer functions**

Create `frontend/src/lib/lead-to-practice.ts`. This file converts a `Lead` object into `BlueprintData` and `MissionControlData` using real enrichment data.

Read `frontend/src/lib/types.ts` first to understand the Lead interface (especially `site_analysis`, `opportunity_reasons`, `opportunity_score`, `tech_stack`, `nicho`).

Read `frontend/src/lib/practice-types.ts` for the target types.

```typescript
import type { Lead } from "./types";
import type { BlueprintData, GapBlock, MissionControlData } from "./practice-types";

export function leadToBlueprintData(lead: Lead): BlueprintData {
  const sa = lead.site_analysis || {};

  const radarScores = {
    seo: sa.has_meta_description ? 65 : (sa.has_structured_data ? 45 : 20),
    performance: typeof sa.pagespeed_score === "number" ? sa.pagespeed_score : 30,
    mobile: sa.is_responsive ? 80 : 15,
    conteudo: (sa.has_structured_data ? 40 : 10) + (lead.top_reviews.length > 3 ? 30 : 10),
    seguranca: sa.has_ssl ? 80 : 10,
    presenca: (lead.website ? 40 : 5) + (Object.keys(lead.social_profiles || {}).length > 0 ? 30 : 5),
  };

  const maturityScore = Math.max(0, Math.min(100, 100 - (lead.opportunity_score || 50)));

  const gaps: GapBlock[] = (lead.opportunity_reasons || []).map(reason => {
    return mapReasonToGap(reason);
  });

  return { radarScores, maturityScore, gaps: gaps.slice(0, 6) };
}
```

**`mapReasonToGap`** function: maps known opportunity_reason strings to GapBlock objects. Handle at least these common reasons:
- "Sem certificado SSL" / "no SSL" -> severity: "critico", solution: "LP profissional com SSL"
- "Site nao responsivo" / "not responsive" -> severity: "fraco", solution: "LP otimizada mobile-first"
- "PageSpeed baixo" / "slow" -> severity: "fraco", solution: "LP com 95+ PageSpeed"
- "Sem dados estruturados" / "no structured data" -> severity: "fraco", solution: "SEO com schema markup"
- "Sem presenca em redes sociais" -> severity: "gap", solution: "Estrategia de presenca digital"
- "Tech stack defasado" -> severity: "fraco", solution: "Stack moderno e otimizado"
- Fallback for unknown reasons: severity: "gap", solution generic

```typescript
export function leadToMissionControlData(lead: Lead): MissionControlData {
  const nicheLabel = lead.nicho || "negocios";

  return {
    pipeline: {
      leadsCaptados: 247,
      outreachEnviado: 74,
      respostas: 15,
      reunioes: 5,
    },
    aiMetrics: {
      custoPorLead: "R$0.42",
      roiIA: "47x",
      leadTimeMedio: "3.2min",
      taxaSucessoAgentes: "94.2%",
    },
    tokensSummary: {
      tokensConsumed: "2.4M",
      totalCost: "R$523",
      revenueAttributed: "R$24.700",
    },
    agents: [
      { name: "Enrichment Agent", successRate: 96.1, calls: 840, cost: "R$187" },
      { name: "LP Generator", successRate: 92.8, calls: 412, cost: "R$264" },
      { name: "Outreach Agent", successRate: 88.5, calls: 342, cost: "R$72" },
    ],
    feed: [
      { type: "lead", title: "Lead qualificado", detail: `${lead.nome} — Score: ${lead.opportunity_score || "N/A"}`, time: "2min" },
      { type: "lp", title: "LP gerada", detail: `${lead.nome} — Landing page personalizada`, time: "8min" },
      { type: "outreach", title: "Outreach enviado", detail: `${lead.nome} — 3 mensagens WhatsApp`, time: "15min" },
      { type: "resposta", title: "Novo lead", detail: `${nicheLabel} na regiao — Score: 78`, time: "32min" },
    ],
    integrations: [
      { name: "WhatsApp", status: "connected" },
      { name: "Analytics", status: "connected" },
      { name: "Claude IA", status: "connected" },
      { name: "CRM", status: "pending" },
    ],
  };
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/lead-to-practice.ts
git commit -m "feat: add Lead to practice data transformer functions"
```

---

### Task 3: Chat Widget (floating)

**Files:**
- Create: `frontend/src/components/shared/chat-widget.tsx`

- [ ] **Step 1: Create the floating chat widget**

Create `frontend/src/components/shared/chat-widget.tsx`. This is a wrapper around `AgentChat` that provides the floating bubble + expandable panel behavior.

Key requirements:
- **Closed state**: circular button (56px) in bottom-right corner (position fixed, right-6, bottom-6, z-50)
  - Avatar with gradient + pulse ring (same style as agent-chat header)
  - Red notification badge showing "1"
- **Open state**: panel 380px wide x 500px tall, bottom-right, with AgentChat inside
  - Header with close button (X)
  - AgentChat fills the panel
  - Backdrop shadow
- **Entry animation**: appears after 4 second delay, slides up from below (translateY)
- **Toggle**: click bubble to open, click X to close
- **Mobile**: panel goes full-width (w-full) with max-h-[70vh]

Component accepts `data: AgentChatData` prop and passes it to AgentChat.

Use Framer Motion for:
- Initial appearance: `motion.div` with `initial={{ opacity: 0, y: 100 }}` `animate={{ opacity: 1, y: 0 }}` after 4s delay
- Panel open/close: `AnimatePresence` with scale + opacity transition

Styling: glassmorphism on panel (same as agent-chat), accent border on bubble, pulse-ring CSS animation on avatar.

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/shared/chat-widget.tsx
git commit -m "feat: add floating chat widget component"
```

---

### Task 4: Modify LP preview page

**Files:**
- Modify: `frontend/src/app/lp/[id]/page.tsx`
- Modify: `frontend/src/components/lp-preview.tsx`

- [ ] **Step 1: Update the LP preview page to fetch full lead and render all components**

Read both files first, then make these changes:

**`frontend/src/app/lp/[id]/page.tsx`** — fetch the full lead object and pass it down:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getLeadByPublicId } from "@/lib/api";
import { LpPreview } from "@/components/lp-preview";
import { ChatWidget } from "@/components/shared/chat-widget";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { buildChatDataForLead } from "@/lib/chat-templates";
import { leadToBlueprintData, leadToMissionControlData } from "@/lib/lead-to-practice";
import type { Lead } from "@/lib/types";

export default function LpPreviewPage() {
  const { id: publicId } = useParams<{ id: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getLeadByPublicId(publicId)
      .then(setLead)
      .catch(() => setError(true));
  }, [publicId]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <p className="text-text-muted text-sm">LP nao encontrada</p>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <span className="w-5 h-5 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  const chatData = buildChatDataForLead(lead);
  const blueprintData = leadToBlueprintData(lead);
  const missionData = leadToMissionControlData(lead);

  return (
    <div className="bg-bg min-h-screen">
      {/* LP Preview (header + iframe) */}
      <LpPreview publicId={publicId} leadName={lead.nome} />

      {/* Intelligence sections below the LP */}
      <div className="max-w-5xl mx-auto px-6 py-16 space-y-20">
        {/* Blueprint Digital */}
        <section>
          <div className="text-center mb-10">
            <p className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-3">Diagnostico Digital</p>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Analise completa: {lead.nome}
            </h2>
          </div>
          <DigitalBlueprint data={blueprintData} />
        </section>

        {/* Mission Control */}
        <section>
          <div className="text-center mb-10">
            <p className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-3">Mission Control</p>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Como voce vai acompanhar tudo
            </h2>
          </div>
          <MissionControl data={missionData} />
        </section>
      </div>

      {/* Floating chat widget */}
      <ChatWidget data={chatData} />
    </div>
  );
}
```

**`frontend/src/components/lp-preview.tsx`** — change from full-page layout to embeddable component:

The current LpPreview uses `h-screen` and `flex flex-col` making it a full-page component. It needs to work as a section within the new page layout. Change:
- Remove `h-screen` from the outer div
- Give the iframe a fixed height instead of `flex-1` (e.g., `h-[80vh]`)
- Keep header, toggle, and iframe behavior intact

Read the file, find `h-screen` and `flex-1` on the iframe, and adjust accordingly.

- [ ] **Step 2: Verify build + lint**

```bash
cd frontend && npm run build && npm run lint
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/lp/\[id\]/page.tsx frontend/src/components/lp-preview.tsx
git commit -m "feat: enrich LP preview with chat widget, blueprint, and mission control"
```

---

### Task 5: QA and polish

- [ ] **Step 1: Run dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Verify in browser**

Check a LP preview page (need a lead with enrichment data, or test with the route structure):
- LP iframe renders correctly (not full screen anymore, ~80vh)
- Scroll down: Blueprint Digital section with radar + gap map (real lead data)
- Scroll more: Mission Control with KPIs, feed (lead name appears), funnel, agents
- After 4 seconds: chat widget bubble slides up in bottom-right
- Click bubble: chat panel opens with niche-appropriate conversation
- Click quick actions: responses appear with typewriter
- Close chat: returns to bubble
- Test responsive: 375px, 768px, 1024px

- [ ] **Step 3: Fix any issues**

Address layout, overflow, z-index conflicts, responsive problems.

- [ ] **Step 4: Final build + lint**

```bash
cd frontend && npm run build && npm run lint
```

- [ ] **Step 5: Commit if fixes were needed**

```bash
git add -A frontend/src/
git commit -m "fix: polish LP preview intelligence layout"
```
