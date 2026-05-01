# Discovery — Bulk Actions + Table View

**Data:** 2026-05-01
**Status:** Discovery (pré-spec)
**Próximos passos:** spec → plan → implementação

## Problema

Operador SDR não consegue executar ações em massa nos leads. Caso recorrente: re-enriquecer 300+ leads de uma coluna do kanban após upgrade de scoring/provider. Hoje só dá pra arrastar 1 por 1. UI também não permite seleção múltipla.

Inspiração: Clay, Apollo, Linear. Padrão consagrado: **view tabela com multi-select + bulk action bar**, em alternativa ao kanban.

## Escopo

Adicionar uma view de tabela paralela ao kanban (toggle, não substituição) com seleção múltipla e ações em massa. Manter kanban como fluxo visual primário; tabela como ferramenta de operação massiva.

## Diagnóstico do estado atual

### Backend (`backend/app/routers/`)

- `pipeline.py` já aceita `lead_ids: number[]` em:
  - `POST /api/pipeline/enrich`
  - `POST /api/pipeline/generate`
  - `POST /api/pipeline/outreach`
  - `POST /api/pipeline/classify`
- `leads.py` tem `PATCH /api/leads/{id}` (per-id) e `DELETE /api/leads/{id}` (per-id). **Sem bulk.**
- `getLeads` aceita filtros: `nicho`, `cidade`, `score_min`, `perfil_lead`, `nicho_canonico`, `search`, `status`, `order_by`, `page`, `per_page`.
- `getLeadCounts` agrega contagem por status com mesmos filtros.

### Frontend (`frontend/src/`)

- `components/kanban-board.tsx` carrega filtros + colunas; cada `kanban-column.tsx` pagina 20 leads/scroll infinito via `getLeads({status, ...filters, page})`.
- Stack: Next.js 16 App Router + React 19 + TS strict + Tailwind v4 + @dnd-kit. State puro via hooks. DS Instrumento (`globals.css` + `components/ui/`).
- `lib/api.ts` é wrapper tipado. `lib/types.ts` tem `Lead`, `KANBAN_COLUMNS`, `LEAD_PROFILE_LABEL`, etc.
- Rota atual `/app/kanban`. Toggle proposto: rota `/app/pipeline?view=kanban|table` (ou similar).

## Decisão arquitetural

| Item | Decisão |
|---|---|
| **View** | Toggle Kanban ↔ Tabela. Kanban mantém. |
| **Lib tabela** | TanStack Table v8 + TanStack Virtual. Headless, integra com DS sem brigar. Virtualização obrigatória pra 300+ rows. |
| **State seleção** | `Set<number>` em React state + sessionStorage (sobrevive F5). |
| **Filtros** | Query string (saved views = só salvar URL depois). |
| **Bulk dispatch** | Até 5000 leads via `lead_ids[]`. Acima de 5000 → futuro endpoint `by_filter` (não build agora). |
| **Saved views scope** | Workspace (`workspace_id=1` constante hoje). User-level fica pra depois. |
| **Updates server-state** | Polling de `/leads/counts` a cada 5s. SSE só se dor aparecer. |
| **Undo bulk** | **Adiado.** Reavaliar após uso. |

## Happy paths (jornadas operador)

| # | Cenário | Fluxo |
|---|---|---|
| H1 | Re-enriquecer coluna após upgrade de scoring | Filtra status → "Selecionar todos N" → "Re-enriquecer" → confirm → job dispara em background |
| H2 | Gerar LP em batch só pros hot | `score_min=70` + `perfil=hot_no_site` + `status=enriched` → select all → "Gerar LP" |
| H3 | Mover batch após call | `status=in_call` → multi-select manual → "Mover para ▾ Fechado" |
| H4 | Limpar lixo | Sem telefone + score<30 → select all → "Excluir" → confirm forte |
| H5 | Handoff colega | Filtra hot da semana → "Exportar CSV" |
| H6 | Outreach por cidade | cidade=Curitiba + status=lp_generated → select all → "Gerar mensagens" |
| H7 | Inspeção rápida | Sort por Score → click linha → abre `/app/leads/[id]` |

## Edge cases

### Seleção
- **Filtro muda com seleção ativa:** manter Set, mostrar `"47 selecionados (3 fora do filtro atual)"` + botão limpar fora do filtro.
- **Select-all página vs all-filter:** checkbox header = só página visível. Banner laranja em cima `"Os 20 desta página estão selecionados. Selecionar todos os 347 →"`.
- **Cross-page select:** Set acumula. Header check vira indeterminate (`-`) quando seleção parcial.
- **F5/navegação:** sessionStorage preserva durante a sessão. Avisa antes se ação destrutiva pendente.
- **Filtro retorna 0 mas Set tem 50:** action bar continua visível com `"47 selecionados (0 visíveis)"`.

### Bulk action
- **Job mesmo tipo já rodando:** desabilita botão. Tooltip explica.
- **Lead já enriquecido na seleção:** modal pergunta `[Sim, todos] [Só os 35 novos] [Cancelar]`. Backend usa `force_providers` quando "todos".
- **Erro parcial:** notif `"Concluído: 42 OK, 5 falharam. [Ver detalhes]"` → modal lista IDs+motivo (já vem em `job.result_summary.errors`).
- **Quota provider:** mostra estimativa antes do dispatch; bloqueia se estourar (depende de endpoint preview — F2+).
- **Race condition:** backend é source of truth. Refetch após bulk.
- **Bulk delete fat-finger:** confirm com typed-input `"Digite EXCLUIR pra confirmar"`.
- **Bulk move pulando etapas:** permite com warning amarelo. Operador é dono do fluxo.

### Performance
- **>5000 leads:** payload IDs vai feio. Limite hard 5k via IDs; acima → endpoint `by_filter` futuro (warning UI ">5000 leads, reduza filtro").
- **Tabela 1k+ linhas:** TanStack Virtual obrigatório.
- **Search:** debounce 300ms.
- **Re-render do Set:** memoizar checkbox cell, table state via TanStack.

### Mobile / densidade
- **<768px:** só Nome+Score+Status visíveis por default. Column visibility menu controla resto.
- **Hit area checkbox:** ≥40px. Long-press = select mode.

### Estado server
- **Polling 5s** em counts + invalida row se status mudou. Banner `"Lista atualizada [aplicar]"` em mudança grande.
- **Job em background:** badge no AppSidebar item Jobs.

### Filtros perversos
- **Filtros esquecidos:** banner sticky topo `"Filtros ativos: cidade=SP, score≥70 [limpar tudo]"`.
- **Input inválido:** validação client-side antes de query.

## Growth loops (build correto desde já)

Ordem de impacto:

| # | Loop | Status | Por quê impacta |
|---|---|---|---|
| G1 | Saved Views (workspace) | Pós-MVP | Multiplica produtividade. Schema preparado já: tabela `saved_views(workspace_id, name, filters JSON, created_by)`. |
| G2 | Smart Segments dinâmicos | Pós-MVP | Saved view + auto-refresh. Drives recurring ops. |
| G3 | Bulk Action Templates (playbooks) | Backlog | "Pipeline express": filtra → enrich → LP → outreach numa sequência. |
| G4 | Schedule routines | Backlog | Saved view + playbook + cron = autopilot. Plug com `/schedule` skill ou Celery beat. |
| G5 | Cost/quota meter ao vivo | Build agora (light) | Endpoint `/pipeline/preview` → `{count, estimated_cost, quota_status}`. Evita estouro provider. |
| G6 | Bulk inline edit | Backlog | Setar `pacote_sugerido` ou tag custom em N leads. |
| G7 | Tags/labels custom | Backlog | Views além do funil fixo. |
| G8 | Funnel/conversão visível | Build agora (light) | Topbar mostra `347 → 89 → 34 → 12 → 3 (0.86%)`. Click filtra. |
| G9 | Activity feed | Backlog | Drive confiança no que rolou em background. |
| G10 | Undo bulk (10s toast) | **Adiado** | User não viu valor agora. Reavaliar. |
| G11 | Insights de operação | Futuro | Detect padrões e sugere automação. |
| G12 | CSV export → import loop | Build agora | Operador anota offline → reimporta via PATCH bulk. |

## Itens a adicionar agora pra suportar growth depois

- Set persistido em sessionStorage (fundamenta saved views).
- Filtros completos em query string (saved view = salvar URL).
- Confirm modal forte (typed) pra delete.
- Banner filtros ativos sticky.
- Polling 5s em counts + diff (base p/ activity feed).
- Job badge no AppSidebar.
- Endpoint `/api/pipeline/preview` retornando `{count, estimated_cost, quota_status}` antes de dispatch.

## Plano em fases (alto nível, antes da spec detalhada)

| Fase | Escopo | Estimativa |
|---|---|---|
| **F1** | Quick win: menu na coluna kanban com "Re-enriquecer coluna" (carrega IDs paginando, chama `runEnrich`) | 1-2h |
| **F2** | Tabela base: rota com toggle, TanStack Table + Virtual, colunas core, filtros compartilhados, sort, virtualização | 1d |
| **F3** | Multi-select: checkboxes, action bar sticky, banner select-all, confirm modals, Set persistido | ½d |
| **F4** | Backend bulk: `PATCH /api/leads/bulk`, `DELETE /api/leads/bulk`, `POST /api/pipeline/preview`. Wire no front. | ½d |
| **F5** | Polimento: column visibility, density toggle, exportar CSV, banner filtros ativos, polling counts | ¼d |

## Decisões travadas (2026-05-01)

1. **Saved views scope:** workspace (não user-level).
2. **Limite bulk:** 5000 hard via IDs. Acima → endpoint `by_filter` futuro.
3. **Lib tabela:** TanStack Table v8 + Virtual.
4. **Undo bulk:** adiado. Reavaliar após uso.

## Pendências pra spec

- Definir colunas exatas da tabela (default + opcionais).
- Definir layout da action bar (posição, breakpoints, ações exatas e ordem).
- Definir contrato do endpoint `/api/pipeline/preview`.
- Definir contrato dos endpoints `bulk` (PATCH + DELETE).
- Definir comportamento exato do "selecionar todos do filtro" quando >5000.
- Definir UX do confirm modal forte (typed-input).
- Definir UX do erro parcial (modal de detalhes).
- Definir formato CSV export.

## Referências de código

- Backend bulk-ready: `backend/app/routers/pipeline.py:144-300` (enrich/generate/outreach já aceitam `lead_ids`).
- Frontend kanban: `frontend/src/components/kanban-board.tsx`, `kanban-column.tsx`.
- API wrapper: `frontend/src/lib/api.ts:118-148` (lead endpoints).
- Tipos: `frontend/src/lib/types.ts` (`Lead`, `KANBAN_COLUMNS`, labels).
- DS: `frontend/src/components/ui/` (Icon, StatusPill, ScoreRing, Badge, Tag, Kbd).
