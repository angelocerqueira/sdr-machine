# Marketing LP — Redesign Instrumento (dark)

**Status:** Spec
**Owner:** Angelo
**Created:** 2026-05-04

## Contexto

A LP marketing atual (`src/app/(marketing)/page.tsx`) foi montada antes do DS Instrumento. Hero usa Remotion com partículas/estrelas (estética cockpit), copy genérica ("Do lead ao cliente. Automático."), e secciona via `BeforeAfter` + `FeaturesGrid` que repetem padrões SaaS sem diferenciação. A nova DS é "anti-cockpit, pró-ofício" — paper/ink, instrumento de trabalho, não dashboard sci-fi. A home não comunica mais com o produto.

Este spec define o redesign completo da home (`/`) — copy, layout, motion e CRO — alinhado com a DS Instrumento e otimizado para o KPI **agendamento de demo**, ICP **times comerciais B2B com SDR interno** (e absorvendo agências de prospecção como caso adjacente).

## Wedge / posicionamento

**Mensagem-âncora:** "Pare de pagar SDR pra abrir LinkedIn."

**Promessa em 4 verbos:** acha · entende · prepara · abre.

**Generalização do output:** O produto não é "LP builder" — é "preparador de abordagem". A copy não menciona LP especificamente. O asset (LP, infográfico, mockup) é parametrizável.

**Microproof único na home:** `500 leads/h · enriquecimento + abordagem prontos`.

## Sequência de sections

| # | Section | Função | Estado |
|---|---------|--------|--------|
| 01 | Hero (B1 dark astrolábio) | Hook + CTA primário | Novo |
| 02 | Trust strip | Logos clientes | Skipped (placeholder) |
| 03 | O Problema | Agita dor | Novo |
| 04 | Promessa em 4 atos | acha · entende · prepara · abre | Substitui FeaturesGrid + BeforeAfter |
| 05 | Veja na Prática | Demo interativa | Redesign do PracticeBlock |
| 06 | Stack que substitui | Comparativo de ferramentas | Novo |
| 07 | Casos / Números | Prova social | Skipped (placeholder) |
| 08 | CTA final | Calendly inline | Substitui CTASection |
| 09 | Footer | Links + contato | Mantém estrutura, adapta visual |

## Tema / paleta

A LP roda **forçada em tema dark**, independente do toggle do app. Razões:
- Hero astrolábio depende de fundo escuro pro contraste de pontos coloridos.
- Diferencia o lado público (vendido) do lado privado (operacional, default light).
- Reforça vibe "instrumento" — telescópio, planimetro, prancheta com lente noturna.

Implementação: `<html data-theme="dark">` forçado no `(marketing)/layout.tsx`. App autenticado mantém respeito ao toggle.

**Tokens-chave usados:**
- BG: `--bg` (ink-0 quente, `#14130f`)
- Texto: `--text` (paper-0, `#f0ebe2`)
- Texto secundário: `--text-secondary` (~55% opacidade do paper)
- Accent: `--accent` (OKLCH blue, `#2b6df0`)
- Mostarda (warm): `#d4a849`
- Terracota (hot): `#e85a3a`
- Salvia (ok): `#88a567`
- Border: `--border` (paper a 8% opacidade)

## Section 01 — Hero

**Layout:** split 1.15fr / 1fr, padding 72px vertical desktop, 48px mobile (stack vertical no mobile).

**Estrutura esquerda:**
```
EYEBROW (mono, mostarda, com traço lateral): PARA TIMES B2B QUE PROSPECTAM EM ESCALA
H1 (Inter Tight 480, 52px desktop / 36px mobile, tracking -0.028em): Pare de pagar SDR pra abrir LinkedIn.
SUB (15px, paper-0 a 55%): SDR Machine acha o lead, lê o que existe sobre ele, prepara a abordagem e abre a conversa. Você define o canal e o material.
CTA1 (azul, sombra azul ~25%): Agendar demo
CTA2 (border paper-soft): Ver em ação ↓
MICRO (mono 10px, paper-0 a 40%): 500 leads/h · enriquecimento + abordagem prontos
```

**Estrutura direita — astrolábio SVG:**
- Container 380px × 380px, drop-shadow azul sutil (~8% opacidade)
- 4 anéis concêntricos (raio 180/148/120/92), opacidades graduais
- Anel mais interno externo dos 120 é **pontilhado mostarda** e gira (60s/volta, linear infinite)
- Crosshair vertical/horizontal + dois diagonais pontilhados
- 4 ticks cardeais sólidos + 4 ticks ordinais opacos
- 4 pontos plotados (leads) com label score em mono ao lado:
  - hot terracota (87, 92) — pulse 2s loop
  - warm mostarda (71)
  - salvia (48)
- Centro azul (`#2b6df0`) com halo respirando — representa "você"
- Label central absoluta: `OPORTUNIDADE TOPO` (mono mostarda) + `87` (Inter Tight 600, 32px, terracota com text-shadow terracota a 40%)

**Background do hero:**
- BG sólido `#14130f`
- Grain sutil (lines 1px, 1.2% opacidade, repeating-linear-gradient horizontal + vertical)
- 2 radial gradients suaves: ellipse azul a 6% no top-right, mostarda a 4% no bottom-left

**Nav:**
- Sticky com fade-down após 80vh scroll
- Logo "SDR Machine" 14px peso 600
- Links: Como funciona · Preço · Login (paper-0 a 70%, hover 100%)
- CTA pill paper-on-ink: bg paper-0, text ink-0, padding 6×14, radius 5

## Section 03 — O Problema

**Layout:** centralizado, max-width 1080px.

**H2 (Inter Tight 480, 44px desktop / 30px mobile):** "Hoje você paga 8 horas de SDR pra entregar 2."

**3 cards (grid 1fr 1fr 1fr desktop, 1col mobile, gap 16px):**
- BG `#1c1a16` (ink-1), border 1px paper-soft a 8%, radius 8px, padding 28px
- Topo: número grande (96px, JetBrains Mono, peso 600, mostarda, tabular-nums)
- Label mono uppercase (10px, paper-0 a 50%, letter-spacing 2.5px)
- Texto curto (14px, paper-0 a 70%, leading 1.5)

| Número | Label | Texto |
|--------|-------|-------|
| `8h` | ABAS · FERRAMENTAS | "40 abas, 12 ferramentas, 0 contexto." |
| `1.2%` | RESPOSTA EM MENSAGEM GENÉRICA | "'Olá, vi que você é dono de…' — copy que ninguém lê." |
| `0%` | CONTEXTO ANTES DA CONVERSA | "Seu SDR fala antes de saber o que dói. O cliente sente." |

**Motion:** stagger fade-up 60ms entre cards. Números count-up de 0 ao valor final em 800ms ao entrar viewport.

## Section 04 — Promessa em 4 atos

**Layout:** 4 sub-sections em zigzag (mockup alterna esquerda/direita, copy do outro lado).

**Container global:** padding 96px vertical desktop, 64px mobile. Cada sub-section: padding 64px vertical desktop, 48px mobile.

**Estrutura por sub-section (cada uma):**
- Eyebrow mono mostarda: `01 · ACHA` (com hífen visual antes)
- H3 (Inter Tight 480, 36px desktop / 26px mobile)
- Sub paragraph (15px, paper-0 a 70%, max-width 480px)
- Lista 3 bullets max (mono 11px, paper-0 a 60%)
- Mockup do produto (50% da largura desktop, full mobile)

**Conteúdo:**

### 01 · ACHA
- **H3:** "Onde seu cliente está. E quem é ele."
- **Sub:** "Pesquisa em Google Maps, Apollo e sua base. Encontra empresas que batem com seu ICP, deduplica, valida CNPJ e enriquece contatos."
- **Bullets:** Filtro nicho × cidade · Deduplicação automática · CNPJ + razão social validados
- **Mockup:** master list de leads agrupada (replica `LaMaster` simplificada — 5 leads, status pills, scores)

### 02 · ENTENDE
- **H3:** "Lê o site. Abre a stack. Entende a dor real."
- **Sub:** "Crawl do site, schema.org, tech stack, reviews do Google. Calcula um score 0-100 com 10+ sinais. Você sabe o que dói antes de falar."
- **Bullets:** 10+ sinais (SSL, mobile, stack, reviews, etc) · Score 0-100 explicável · Reasons em texto pronto
- **Mockup:** painel de diagnóstico (4 dim bars, ScoreRing, reasons list — replica `LaTabDiag`)

### 03 · PREPARA
- **H3:** "Material certo. Pra esse lead. Em segundos."
- **Sub:** "Gera o asset de abordagem que faz sentido pro lead — landing page personalizada, infográfico de diagnóstico, mockup. Tudo público, sem login, pronto pra enviar."
- **Bullets:** Templates conectados ao diagnóstico · LP, infográfico ou mockup · URL pública dedicada
- **Mockup:** asset gallery (3 thumbs lado a lado: LP · infográfico · mockup)

### 04 · ABRE
- **H3:** "Mensagem pronta. No canal certo. Em pt-BR humano."
- **Sub:** "Compõe abordagem inicial, follow-up de 48h e mensagem final. Link wa.me pré-preenchido. Tom configurável (formal, parceiro, direto)."
- **Bullets:** 3 cadências por lead · WhatsApp, e-mail, ligação · Tom configurável
- **Mockup:** 3 mensagens em cards stacked + botão WA pré-preenchido

**Motion:** ao entrar viewport, copy fade-up 60ms stagger, mockup slide-up 24px com fade. Mockups têm microloop interno (ex: status pill ciclando entre `enriquecido → LP gerada → WA enviado` em 4s loop).

## Section 05 — Veja na Prática

Redesign do `PracticeBlock` no DS dark, mantendo estrutura interativa atual e os dados de `practice-data.ts`.

**Layout:**
- H2: "Veja em prática. Sem rodar nada."
- Sub: "Escolha um nicho × cidade e veja o que sairia da máquina."
- Controle: 2 dropdowns mono (nicho · cidade) + botão "Rodar" azul
- Output panel: grid 1fr 1.5fr, lead card à esquerda + diagnóstico/asset/msg à direita

**Output panel:**
- Lead card: nome, badge nicho, cidade, score ring 87, reviews count
- Painel direito: 3 abas mini — Diagnóstico · Asset · Mensagem (default = Diagnóstico)
- Trocar nicho/cidade anima output com fade + slide 12px (~250ms)

## Section 06 — Stack que substitui

**Layout:** centralizado.

**H2:** "Hoje, a mesma entrega usa 5 ferramentas."

**Comparativo (visual):**
- 5 logo placeholders cinza (Apollo, Lusha, ChatGPT, Mailshake, Carrd) lado a lado, cada um com X terracota sobreposto
- Seta vertical descendo (paper-0 a 30%)
- 1 logo "SDR Machine" centralizado abaixo, em paper-0 sólido, com glow azul sutil

**Footnote (mono, paper-0 a 50%, centralizado):** "+ 8h/dia de SDR consolidando manualmente."

**Motion:** ao entrar viewport, X de cada logo "carimba" em sequência (80ms stagger, scale 1.2 → 1, opacity 0 → 1). Logo final entra com fade-up 200ms após último X.

## Section 08 — CTA Final

**BG:** ink-1 (`#1c1a16`), com astrolábio reduzido (160px) como decoração lateral direita, opacidade 30%, sem rotação.

**Layout:** centralizado, max-width 720px.

```
H2 (Inter Tight 480, 44px): Pronto pra parar de pagar
                            SDR pra abrir LinkedIn?
SUB (15px, paper-0 a 70%):  15 min de demo. Roda na sua base. Sem compromisso.

[ CALENDLY EMBED INLINE — 600px height, border 1px paper-soft, radius 8px ]

MICRO (mono, paper-0 a 50%): Resposta em <2h
```

Calendly embed real (não modal) — script oficial. URL configurada via env var `NEXT_PUBLIC_CALENDLY_URL`.

## Section 09 — Footer

**Layout:** padding 64px vertical, border-top 1px paper-soft.

- Linha superior (grid 2fr 3fr):
  - Logo "SDR Machine" + tagline "Instrumento de prospecção"
  - 3 colunas (Produto · Empresa · Legal) — links verticais paper-0 a 60%
- Linha inferior (flex justify-between):
  - "© 2026 Sollertis"
  - Ícone LinkedIn (Icon DS), hover paper-0 sólido

## Sistema de motion

**Princípios:**
- Total movement budget: <2% da tela em qualquer momento.
- Tudo respeita `prefers-reduced-motion: reduce` — fade only, sem translate/scale.
- Easing default: `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out forte).
- Duration: 250-400ms entradas, 800ms count-ups.

**Padrões reutilizados (hooks/utils):**
- `useFadeUpOnView` — IntersectionObserver, threshold 0.2, fade-up 24px.
- `useStagger` — delay 60ms entre filhos diretos.
- `useCountUp` — anima de 0 ao valor final, tabular-nums, 800ms.
- `useMockupLoop` — ciclo de estados em mockup (status pills, cursor).

**Sticky nav:** aparece com slide-down 200ms quando `window.scrollY > 80vh`.

## CRO patterns

- 3 momentos de CTA principal: hero · final de seção 05 ("agendar demo" link inline no fim do output) · seção 08 (Calendly embed).
- Sticky nav sempre acessível com botão "Agendar demo" após scroll do hero.
- Sem modais, sem overlays. Calendly embed inline minimiza fricção.
- Sem campo de email ou waitlist — sales-led puro.
- Sem fold de "self-serve" / "signup grátis" — a única ação é agendar demo.

## Mudanças no código

### Arquivos novos
- `frontend/src/components/marketing/hero-astrolabe.tsx` — novo hero (substitui `hero-section.tsx`)
- `frontend/src/components/marketing/hero-astrolabe.module.css` — SVG astrolábio + animations
- `frontend/src/components/marketing/problem-section.tsx` — section 03
- `frontend/src/components/marketing/promise-acts.tsx` — section 04 (4 sub-sections)
- `frontend/src/components/marketing/promise-mockups/` — 4 mini-mockups (acha, entende, prepara, abre)
- `frontend/src/components/marketing/stack-substitutes.tsx` — section 06
- `frontend/src/components/marketing/cta-calendly.tsx` — section 08 com embed
- `frontend/src/components/marketing/lp-motion.ts` — hooks de motion (`useFadeUpOnView`, `useStagger`, `useCountUp`, `useMockupLoop`)

### Arquivos modificados
- `frontend/src/app/(marketing)/page.tsx` — nova sequência de sections
- `frontend/src/app/(marketing)/layout.tsx` — força `data-theme="dark"` localmente, sem alterar persistência do app
- `frontend/src/components/marketing/marketing-navbar.tsx` — sticky com slide-down, ajuste pra theme dark
- `frontend/src/components/marketing/practice-block.tsx` — redesign visual no DS dark, lógica preservada
- `frontend/src/components/marketing/marketing-footer.tsx` — adaptação visual

### Arquivos removidos / substituídos
- `frontend/src/components/marketing/hero-section.tsx` (substituído por `hero-astrolabe`)
- `frontend/src/components/marketing/before-after.tsx` (substituído por `problem-section`)
- `frontend/src/components/marketing/features-grid.tsx` (substituído por `promise-acts`)
- `frontend/src/components/marketing/cta-section.tsx` (substituído por `cta-calendly`)
- `frontend/src/components/marketing/pipeline-section.tsx` (conteúdo absorvido por `promise-acts`)
- Hero Remotion + composition (`components/remotion/hero-composition.tsx`) — não usado mais na LP. Mantém arquivo se for usado em outro lugar; checar referências antes de deletar.

### Env vars
- Nova: `NEXT_PUBLIC_CALENDLY_URL` — URL pública do Calendly da equipe. Documentar em `.env.example`.

### Trust strip e Casos (skipped)
- Componentes não criados nesta iteração.
- Comentário no `page.tsx` indicando posição reservada.

## Out of scope

- Pricing page / pricing section
- Self-serve signup / trial
- A/B testing infra (variantes de copy ficam pra fase 2)
- Storybook das mockups (preparar componentes pra reuso só se aparecer demanda)
- Tradução / i18n (pt-BR fixo)
- Analytics adicional (eventos de conversão Calendly herdam do `posthog` se já configurado)

## Mobile-first (CLAUDE.md)

Todas as sections em `min-width` breakpoints. Ordem de definição: mobile (default) → 640px (sm) → 1024px (lg). Hero stacka vertical, astrolábio em 240px no mobile, 380px desktop. Sub-sections de "Promessa" sempre stack vertical no mobile (mockup primeiro, copy depois). Calendly embed responsive.

## Critérios de aceitação

1. `/` em desktop e mobile renderiza no DS Instrumento dark sem usar Remotion.
2. Hero contém astrolábio SVG funcional com pontos plotados, anel pontilhado girando, centro azul respirando, label "OPORTUNIDADE TOPO · 87".
3. Copy do hero exata: H1 "Pare de pagar SDR pra abrir LinkedIn." Sub conforme spec.
4. 4 sub-sections de "Promessa em 4 atos" com mockups visuais distintos (não placeholders).
5. Section 06 (Stack que substitui) anima o "X carimbando" nos 5 logos.
6. Calendly embed real funciona com `NEXT_PUBLIC_CALENDLY_URL`.
7. `prefers-reduced-motion` desativa todas as animações de translate/scale.
8. Lighthouse Performance >85 desktop, >75 mobile (sem regressão grande vs versão atual).
9. Lint sem erros.
