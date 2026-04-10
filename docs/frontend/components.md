# Catálogo de Componentes

Referência técnica de todos os componentes React do frontend do SDR Machine. Cada componente é um arquivo `.tsx` em `frontend/src/components/` -- sem subdiretórios, sem barrel exports.

---

## Mapa de Componentes

Hierarquia de quais páginas usam quais componentes:

```
app/(main)/layout.tsx
├── Sidebar
├── SignOutButton
│
├── page.tsx (Dashboard)
│   └── StatsCard
│
├── kanban/page.tsx
│   ├── PipelineControls
│   │   ├── JobProgress
│   │   ├── ScrapeModal
│   │   └── ConfirmModal
│   └── KanbanBoard
│       ├── KanbanColumn
│       │   └── KanbanCard
│       └── LeadSheet
│           ├── DiagnosticPanel
│           ├── ServiceLevelTabs
│           └── ConfirmModal
│
├── jobs/page.tsx
│   └── (JobDetailModal -- inline, não é componente separado)
│
└── leads/[id]/page.tsx
    ├── LeadDetail
    │   ├── DiagnosticPanel
    │   └── ServiceLevelTabs
    └── WhatsAppButton

app/lp/[id]/page.tsx
└── LpPreview
```

---

## Pipeline

Componentes responsáveis por controlar e monitorar a execução das 4 fases do pipeline (scrape, enrich, generate, outreach).

### PipelineControls

- **Arquivo:** `pipeline-controls.tsx`
- **Responsabilidade:** Renderiza os 4 botões do pipeline (Scraping, Enriquecer, Gerar LPs, Outreach), gerencia a execução de jobs e exibe progresso em tempo real.
- **Props:**
  - `onJobDone?: () => void` -- callback chamado quando um job termina (na page do Kanban, recarrega a página).
- **State:**
  - `activeJob: Job | null` -- job em execução no momento.
  - `error: string | null` -- mensagem de erro da última tentativa.
  - `eligibleCounts: Record<string, number>` -- contagem de leads elegíveis por fase.
  - `runningJobs: string[]` -- fases com jobs em execução (desabilita botões).
  - `pendingPhase` -- fase aguardando confirmação do usuário antes de iniciar.
  - `enabledProviders: Set<string>` -- providers de enriquecimento habilitados (inicializado com todos do `ENRICH_PROVIDERS`).
  - `showProviders: boolean` -- toggle para exibir/ocultar lista de providers na modal de enrich.
- **API calls:**
  - `getPipelineStatus()` -- carrega `eligible_counts` e `running_jobs` (roda no mount e quando `activeJob` muda).
  - `runScrape(params)`, `runEnrich(params)`, `runGenerate(params)`, `runOutreach(params)` -- dispara a fase selecionada.
- **Interações do usuário:**
  - Clicar em um botão de fase abre um modal de confirmação (`ConfirmModal` ou `ScrapeModal`).
  - Para a fase "enrich", o modal inclui checkboxes para habilitar/desabilitar providers de enriquecimento.
  - Confirmar inicia o job e renderiza o `JobProgress` inline.
  - Ao término do job, chama `onJobDone`.

### JobProgress

- **Arquivo:** `job-progress.tsx`
- **Responsabilidade:** Exibe o progresso de um job em tempo real via SSE, com log scrollável e indicador de status (rodando / concluído / erro).
- **Props:**
  - `jobId: number` -- ID do job a monitorar.
  - `onDone?: () => void` -- callback disparado quando o job emite evento `done`.
- **State:**
  - `messages: string[]` -- lista de mensagens de log recebidas via SSE.
  - `status: "running" | "done" | "error"` -- estado atual do job.
- **API calls:**
  - `streamJob(jobId, onEvent)` -- abre um stream SSE em `GET /api/jobs/{id}/stream`. Recebe eventos `{ type, message }`. Fecha automaticamente em "done" ou "error".
- **Interações do usuário:**
  - Componente é somente leitura. O log faz auto-scroll para o final conforme novas mensagens chegam.

---

## Kanban

Componentes do board de Kanban com drag-and-drop para visualização e gestão do pipeline de leads.

### KanbanBoard

- **Arquivo:** `kanban-board.tsx`
- **Responsabilidade:** Renderiza o board completo com filtros, colunas (uma por status) e o painel lateral de detalhes. Gerencia drag-and-drop via `@dnd-kit/core`.
- **Props:** Nenhuma.
- **State:**
  - `counts: Record<string, number>` -- contagem de leads por status (alimenta os badges das colunas).
  - `nichos: string[]` / `cidades: string[]` -- valores únicos para os selects de filtro.
  - `loading: boolean` -- estado de carregamento inicial.
  - `filterNicho`, `filterCidade`, `filterScoreMin`, `search` -- filtros ativos.
  - `orderBy: string` -- ordenação atual (default: `"score_desc"`).
  - `selectedLeadId: number | null` -- ID do lead aberto no `LeadSheet`.
  - `refreshKeys: Record<string, number>` -- contadores por coluna, incrementados para forçar refetch após drag-and-drop.
- **Hooks:** `useState`, `useEffect`, `useCallback`. Usa `useSensor` e `useSensors` do `@dnd-kit/core` com `PointerSensor` (distância mínima de ativação: 8px).
- **API calls:**
  - `getLeadCounts(params)` -- contagem de leads por status, respeitando filtros.
  - `getLeadFilters()` -- lista de nichos e cidades únicos para os selects.
  - `updateLead(id, { status })` -- chamado no `handleDragEnd` para atualizar o status do lead.
- **Interações do usuário:**
  - Digitar no campo de busca filtra por nome ou telefone.
  - Selecionar nicho, cidade ou score mínimo filtra as colunas.
  - Selecionar ordenação muda a ordem dos cards em todas as colunas.
  - Arrastar um card de uma coluna para outra faz update otimista de contagens e chama a API.
  - Clicar em um card abre o `LeadSheet` lateral.

### KanbanColumn

- **Arquivo:** `kanban-column.tsx`
- **Responsabilidade:** Renderiza uma coluna do Kanban com header (label + contagem), lista de cards com scroll infinito e estado de drop zone via `@dnd-kit/core`.
- **Props:**
  - `id: string` -- status da coluna (ex: `"scraped"`, `"enriched"`).
  - `label: string` -- label exibido no header.
  - `count: number` -- contagem de leads (vinda do pai).
  - `refreshKey: number` -- incremento força refetch da coluna.
  - `filterNicho?`, `filterCidade?`, `filterScoreMin?`, `search?`, `orderBy?` -- filtros propagados do `KanbanBoard`.
  - `onSelectLead: (id: number) => void` -- callback ao clicar em um card.
- **State:**
  - `leads: Lead[]` -- leads carregados para esta coluna.
  - `page: number` -- página atual para paginação.
  - `total: number` -- total de leads neste status.
  - `loading` / `loadingMore` -- estados de carregamento inicial e scroll infinito.
- **Hooks:** `useState`, `useEffect`, `useCallback`, `useRef`. Usa `useDroppable` do `@dnd-kit/core`.
- **API calls:**
  - `getLeads(params)` -- busca leads paginados por status, com filtros e ordenação. PER_PAGE = 20.
- **Interações do usuário:**
  - Scroll infinito: ao chegar perto do final (< 80px), carrega a próxima página automaticamente.
  - Aceita drops de cards de outras colunas (visual feedback com borda accent).
  - Colunas `disqualified` e `failed` têm estilo visual diferenciado (borda e fundo danger).

### KanbanCard

- **Arquivo:** `kanban-card.tsx`
- **Responsabilidade:** Renderiza um card de lead dentro de uma coluna do Kanban. Exibe nome, nicho, score de oportunidade, rating e cidade. Suporta drag via `@dnd-kit/core`.
- **Props:**
  - `lead: Lead` -- dados do lead.
  - `onSelect: (id: number) => void` -- callback ao clicar no card.
- **State:** Nenhum state próprio.
- **Hooks:** `useDraggable` do `@dnd-kit/core` -- registra o card como draggable, passa `{ lead }` em `data.current`.
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - Arrastar o card para outra coluna (cursor muda para `grab`/`grabbing`).
  - Clicar no card chama `onSelect(lead.id)`.
  - Hover sobre o score exibe tooltip com até 4 `opportunity_reasons`.
  - A borda esquerda do card é colorida pelo score: verde (>= 60), amarelo (>= 40), neutro (< 40).

---

## Lead Detail

Componentes para exibição detalhada de um lead, diagnóstico de marketing e níveis de serviço.

### LeadSheet

- **Arquivo:** `lead-sheet.tsx`
- **Responsabilidade:** Painel lateral deslizante (slide-out sheet) que exibe os detalhes completos de um lead. Inclui informações gerais, gaps detectados, fontes de enriquecimento, diagnóstico, preview da LP, histórico de versões da LP, mensagens de outreach, e botões de ação contextual.
- **Props:**
  - `leadId: number | null` -- ID do lead a exibir (null = fechado).
  - `onClose: () => void` -- callback para fechar o painel.
- **State:**
  - `lead: Lead | null` -- dados do lead.
  - `messages: OutreachMessage[]` -- mensagens de outreach do lead.
  - `loading: boolean` -- estado de carregamento.
  - `actionLoading: boolean` -- indica que uma ação (enrich/generate/outreach) está em execução.
  - `pendingAction: "enrich" | "generate" | "regenerate" | "outreach" | "re-enrich" | "retry" | null` -- ação aguardando confirmação.
  - `landingPages: LandingPage[]` -- lista de versões de LP do lead.
  - `activatingLpId: number | null` -- ID da LP sendo ativada.
- **Hooks:** `useState`, `useEffect`, `useCallback`. Listener de `Escape` para fechar.
- **API calls:**
  - `getLead(id)` -- busca dados do lead.
  - `getLeadMessages(id)` -- busca mensagens de outreach.
  - `getLeadLandingPages(id)` -- busca versões de landing pages.
  - `getLeadLpUrl(id)` -- gera URL do iframe para preview da LP.
  - `activateLandingPage(leadId, lpId)` -- ativa uma versão específica da LP.
  - `runEnrich({ lead_ids })`, `runGenerate({ lead_ids })`, `runOutreach({ lead_ids })` -- executa ações individuais no lead.
- **Interações do usuário:**
  - Fechar: clicar no backdrop, no botão X, ou pressionar `Escape`.
  - Botões de ação contextual aparecem conforme o status do lead:
    - `scraped` -> "Enriquecer"
    - `enriched` -> "Gerar LP"
    - `lp_generated` -> "Gerar Outreach" + "Regenerar LP"
    - `outreach_ready` -> "Regenerar LP"
    - `disqualified` -> "Re-enriquecer"
    - `*_failed` -> "Reprocessar"
  - Cada ação abre um `ConfirmModal` antes de executar.
  - No histórico de LPs, clicar em "Ativar" define uma versão como ativa.
  - Mensagens de outreach exibem botão "Abrir WhatsApp" com link pre-filled.

### LeadDetail

- **Arquivo:** `lead-detail.tsx`
- **Responsabilidade:** Renderiza a visão detalhada de um lead com header (nome, nicho, cidade, score), grid de informações (telefone, rating, website, status), gaps detectados, diagnóstico de marketing (via `DiagnosticPanel` ou `ServiceLevelTabs`), e preview da LP em iframe.
- **Props:**
  - `lead: Lead` -- dados completos do lead.
- **State:** Nenhum state próprio.
- **API calls:**
  - `getLeadLpUrl(id)` -- gera URL para o iframe de preview da LP.
- **Interações do usuário:**
  - Link "Tela cheia" abre a LP em nova aba via `/lp/{public_id}`.

### DiagnosticPanel

- **Arquivo:** `diagnostic-panel.tsx`
- **Responsabilidade:** Exibe o diagnóstico de marketing gerado pela IA, incluindo resumo executivo, momento no funil de marketing, potencial de IA/automação, top 3 prioridades, e detalhes por etapa do funil. Suporta modo compacto (usado no `LeadDetail`) e modo completo (usado no `LeadSheet`).
- **Props:**
  - `siteAnalysis: Record<string, unknown>` -- objeto `site_analysis` do lead. O componente extrai o campo `diagnostico_marketing`.
  - `compact?: boolean` -- modo compacto omite detalhes do funil (default: `false`).
- **State:** Nenhum state próprio.
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - No modo completo, seção "Detalhes por Etapa do Funil" é um `<details>` colapsável.
- **Sub-componentes internos:**
  - `IAPotentialCard` -- exibe score de potencial de IA, barra de progresso e tags de oportunidades.
  - `PrioridadesCard` -- exibe top 3 prioridades numeradas.

### ServiceLevelTabs

- **Arquivo:** `service-level-tabs.tsx`
- **Responsabilidade:** Exibe o diagnóstico baseado em níveis de serviço (LP, Automação Básica, Mapa+Automações, Vertical OS) com abas interativas. Mostra o nível recomendado, resumo executivo e, para cada nível, score, sinais detectados, oportunidades e justificativa.
- **Props:**
  - `serviceLevels: ServiceLevels` -- objeto com scores e dados para cada nível de serviço.
- **State:**
  - `activeTab: NivelKey` -- aba ativa (inicializada com `serviceLevels.nivel_recomendado`).
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - Clicar nas abas alterna entre os 4 níveis de serviço (LP, Automação, Mapa+Auto, OS).
  - Cada aba mostra o score numérico; a aba ativa tem indicador de barra inferior; o nível recomendado tem um dot verde.
  - Se o lead foi desqualificado, exibe banner de desqualificação com motivo.

---

## Modals

### ScrapeModal

- **Arquivo:** `scrape-modal.tsx`
- **Responsabilidade:** Modal para configurar os parâmetros de um job de scraping: nichos, cidades (com suporte a múltiplos valores via tags) e máximo de resultados por busca.
- **Props:**
  - `open: boolean` -- controla visibilidade.
  - `onConfirm: (params: { nichos: string[]; cidades: string[]; max_results: number }) => void` -- callback com os parâmetros configurados.
  - `onCancel: () => void` -- callback para fechar.
- **State:**
  - `nichos: string[]` / `cidades: string[]` -- listas de tags já adicionadas.
  - `nichoInput` / `cidadeInput` -- texto dos inputs.
  - `maxResults: number` -- máximo de resultados (default: 50, range: 1-100).
  - `suggestedNichos` / `suggestedCidades` -- sugestões vindas do backend.
- **API calls:**
  - `getSettings()` -- busca `target_niches` e `target_cities` para sugestões via `<datalist>`.
- **Interações do usuário:**
  - Digitar nicho/cidade e pressionar Enter adiciona como tag.
  - Tags podem ser removidas com o botão "x".
  - Sugestões aparecem via datalist nativo do navegador.
  - `Escape` fecha o modal.
  - Botão "Executar Scraping" fica desabilitado se nichos ou cidades estiverem vazios.

### ConfirmModal

- **Arquivo:** `confirm-modal.tsx`
- **Responsabilidade:** Modal genérico de confirmação com título, conteúdo customizável (children), e dois botões (Cancelar + Confirmar).
- **Props:**
  - `open: boolean` -- controla visibilidade.
  - `title: string` -- título do modal.
  - `children: React.ReactNode` -- conteúdo do corpo.
  - `confirmLabel?: string` -- texto do botão de confirmação (default: `"Confirmar"`).
  - `confirmVariant?: "accent" | "danger"` -- estilo do botão (default: `"accent"`).
  - `onConfirm: () => void` -- callback ao confirmar.
  - `onCancel: () => void` -- callback ao cancelar.
- **State:** Nenhum.
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - Clicar no backdrop ou pressionar `Escape` fecha o modal (chama `onCancel`).
  - Clicar em "Confirmar" chama `onConfirm`.

---

## UI Primitives

### Sidebar

- **Arquivo:** `sidebar.tsx`
- **Responsabilidade:** Barra lateral de navegação fixa com branding (logo + versão) e links para Dashboard, Kanban e Jobs. Destaca a rota ativa com indicador visual e fundo diferenciado.
- **Props:** Nenhuma.
- **State:** Nenhum state próprio.
- **Hooks:** `usePathname()` do Next.js para detectar a rota ativa.
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - Clicar nos links navega entre as páginas.
  - Rotas: `/` (Dashboard), `/kanban` (Kanban), `/jobs` (Jobs).
- **Rotas definidas em `NAV_ITEMS`:**
  ```ts
  const NAV_ITEMS = [
    { href: "/", label: "Dashboard", icon: DashboardIcon },
    { href: "/kanban", label: "Kanban", icon: KanbanIcon },
    { href: "/jobs", label: "Jobs", icon: JobsIcon },
  ];
  ```

### StatsCard

- **Arquivo:** `stats-card.tsx`
- **Responsabilidade:** Card de estatística com label, valor numérico grande e ícone. Suporta variante "accent" para destaque visual.
- **Props:**
  - `label: string` -- texto do label superior.
  - `value: string | number` -- valor a exibir.
  - `icon: React.ReactNode` -- ícone SVG.
  - `accent?: boolean` -- se true, usa bordas e fundo accent.
- **State:** Nenhum.
- **API calls:** Nenhuma.
- **Interações do usuário:** Nenhuma -- componente puramente visual.

### LpPreview

- **Arquivo:** `lp-preview.tsx`
- **Responsabilidade:** Página de preview de landing page em tela cheia com toggle entre modo desktop (iframe 100%) e mobile (iframe dentro de simulação de iPhone com Dynamic Island).
- **Props:**
  - `publicId: string` -- ID público do lead para gerar URL da LP.
  - `leadName: string` -- nome do lead exibido no header.
- **State:**
  - `mode: "desktop" | "mobile"` -- modo de visualização atual.
- **Hooks:** `useRouter()` do Next.js para navegação "Voltar".
- **API calls:**
  - `getLeadLpUrlByPublicId(publicId)` -- gera URL do iframe (não faz fetch, apenas compõe a URL).
- **Interações do usuário:**
  - Toggle Desktop/Mobile com botões no header.
  - Botão "Voltar" navega para a página anterior (ou para `/kanban` se não houver histórico).

### WhatsAppButton

- **Arquivo:** `whatsapp-button.tsx`
- **Responsabilidade:** Botão estilizado para abrir link do WhatsApp (wa.me) e, opcionalmente, botão para marcar mensagem como enviada.
- **Props:**
  - `whatsappLink: string` -- URL wa.me com mensagem pre-filled.
  - `onMarkSent?: () => void` -- callback para marcar como enviada (se fornecido, renderiza botão extra).
- **State:** Nenhum.
- **API calls:** Nenhuma.
- **Interações do usuário:**
  - "Abrir WhatsApp" abre o link em nova aba.
  - "Marcar como enviado" chama `onMarkSent` (na page `leads/[id]`, faz `updateLead(id, { status: "outreach_sent" })`).

### SignOutButton

- **Arquivo:** `sign-out-button.tsx`
- **Responsabilidade:** Botão de logout que chama `authClient.signOut()` do Better Auth e redireciona para `/login`.
- **Props:** Nenhuma.
- **State:** Nenhum.
- **Hooks:** `useRouter()` do Next.js.
- **API calls:**
  - `authClient.signOut()` -- encerra a sessão via Better Auth.
- **Interações do usuário:**
  - Clicar no botão "Sair" faz logout e redireciona para a página de login.
