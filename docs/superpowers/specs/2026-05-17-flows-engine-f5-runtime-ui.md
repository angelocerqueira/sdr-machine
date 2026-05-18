# Flows Engine — F-5 Runtime UI Spec

> **Foundation:** [F-0](2026-05-17-flows-engine-f0-architecture.md) · [F-3](2026-05-17-flows-engine-f3-triggers-api.md)
> **Status:** ready to plan
> **Depende:** F-3 (API runs + steps)
> **Stack:** Next.js 16 App Router + DS Instrumento + SWR polling

## 1. Objetivo

Telas pra **observar e debugar** runs em produção. Sem isso, o user habilita um flow e fica cego — não sabe se rodou, onde travou, quantos leads passaram.

Não inclui métricas agregadas (heatmap, taxas) — fica pra v2. F-5 cobre o essencial: lista de runs + detalhe step-by-step + visualização do progresso no editor.

## 2. Rotas

```
frontend/src/app/app/flows/
├── [id]/page.tsx                       # editor (F-4) — adicionar tab "Runs"
└── [id]/runs/
    ├── page.tsx                        # lista de runs do flow
    └── [run_id]/page.tsx               # detalhe step-by-step
```

## 3. Estrutura

```
frontend/src/components/flows/runs/
├── RunsList.tsx                # tabela de runs filtrável
├── RunsFilters.tsx             # chips: status, lead search, date range
├── RunStatusPill.tsx           # pending/running/waiting/completed/cancelled/failed
├── RunDetail.tsx               # header com lead + flow + status + actions
├── RunStepsTimeline.tsx        # lista vertical de FlowRunStep
├── RunStepCard.tsx             # 1 step: node icon + status + duration + payload preview
├── RunFlowOverlay.tsx          # mini-editor read-only com node atual destacado
└── RunActions.tsx              # cancelar, retry (se failed), ver lead
```

## 4. Lista de runs (`/app/flows/[id]/runs`)

Tabela:

| Status | Lead | Node atual | Próximo evento | Iniciado | Duração |
|---|---|---|---|---|---|
| 🟢 running | Acme Cia (5544...) | send_whatsapp | — | há 12s | 12s |
| 🟡 waiting | Beta Ltda (5511...) | wait | em 1h 23min | há 2d | 2d |
| 🟢 completed | Gama SA (5599...) | end | — | há 5d | 8d |
| 🔴 failed | Delta Co | send_whatsapp | — | há 1h | 1m | (erro: provider 500) |
| ⚫ cancelled | Epsilon | wait | — | há 3d | 1d |

Filtros:
- Status (multi-select chips)
- Search por nome/telefone/email do lead
- Date range (started_at)

Polling SWR `refreshInterval: 10000` (10s) — runs ativos atualizam visualmente.

Click linha → `/app/flows/[id]/runs/[run_id]`.

## 5. Detalhe run (`/app/flows/[id]/runs/[run_id]`)

### Header
- Lead nome + link pro Lead App
- Flow name + versão (`v3`) + link pro editor
- Status pill + duração desde started_at
- Botões: **Cancelar** (se ativo), **Re-executar** (se failed), **Ver lead**

### Layout duas colunas

```
┌────────────────────────────────┬─────────────────────────────┐
│ Timeline                       │ Flow Overlay                │
│                                │                             │
│ ● Start (12:01)         100ms  │ ┌─────┐                     │
│ ● Send WA (12:01)       450ms  │ │Start│                     │
│   ↳ "Olá Acme, vi seu..."      │ └──┬──┘                     │
│ ● Wait 2d (12:02 → 14/05)      │ ┌──▼──────┐                 │
│ ● Send WA (15:00 14/05) 380ms  │ │Send WA  │ ✓               │
│   ↳ "Acompanhando..."          │ └──┬──────┘                 │
│ ◐ Branch on reply              │ ┌──▼──────┐                 │
│   ↳ window 1d, aguardando      │ │Wait 2d  │ ✓               │
│                                │ └──┬──────┘                 │
│ (aguardando próximo step)      │ ┌──▼──────┐                 │
│                                │ │Send WA  │ ✓               │
│                                │ └──┬──────┘                 │
│                                │ ┌──▼──────┐                 │
│                                │ │Branch   │ ⚪ executing    │
│                                │ └─┬─────┬─┘                 │
│                                │   yes   no                  │
└────────────────────────────────┴─────────────────────────────┘
```

**Timeline** (esquerda): lista vertical de FlowRunStep com:
- Indicador status (●●●◐ ◯)
- Nome do node + tipo + timestamp
- Duração (ms)
- Payload preview (clicável → modal expandido)
- Erro highlight em vermelho se step failed

**Flow Overlay** (direita): mini-renderização read-only do flow (reusa custom nodes do F-4 com prop `mode="readonly"`) com:
- Nodes já executados marcados ✓ verde
- Node atual highlighted (pulsing)
- Edges traversadas destacadas (cor accent)
- Edges não tomadas dimmed

Polling SWR 5s em `/api/flows/runs/{id}` + `/api/flows/runs/{id}/steps`.

## 6. Step detail modal

Click num step abre modal:

```
┌────────────────────────────────────────────┐
│ Send WhatsApp — node send-wa-1             │
│                                            │
│ Status: ✓ success                          │
│ Iniciado: 12:01:23 · Duração: 450ms        │
│                                            │
│ Input (rendered body):                     │
│ ┌────────────────────────────────────────┐ │
│ │ Olá Acme, vi seu negócio em Chapecó   │ │
│ │ no nicho de dentista...                │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ Output:                                    │
│ • provider_message_id: EVO-abc123          │
│ • sent_at: 12:01:23                        │
│                                            │
│ [Ver conversa no Inbox →]                  │
└────────────────────────────────────────────┘
```

Se failed:
```
Status: ✗ failed
Erro: provider returned 500
Retry: 2/3 (próximo em 4min)
```

## 7. Tab "Runs" no editor

No `/app/flows/[id]/page.tsx` (editor), adicionar tabs no topo:

```
[Editor] [Runs (42 ativos · 156 concluídos)]
```

Tab "Runs" mostra a lista (componente `RunsList`) embedded, sem navegar fora. Bom pra workflow de "estou editando, quero ver impacto" — fica tudo no mesmo route.

## 8. Ações

### Cancelar run (status ativos)
- `DELETE /api/flows/runs/{id}` → run vira `cancelled` com `cancel_reason="manual"`
- Confirm dialog: "Cancelar essa execução? Não pode desfazer."

### Re-executar (status failed)
- `POST /api/flows/runs/{id}/retry` (endpoint novo em F-3? Sim, atrelar a esse spec ou fazer F-5.5)
- Cria novo FlowRun pra mesmo lead+flow, current_node = node onde falhou. State preservado.

### Ver lead
- Navega pro Lead App `/app/leads?selected=<lead_id>`

## 9. Métricas básicas no header da página de lista

```
┌────────────────────────────────────────────────────────────┐
│ Prospecção fria · v3 · ✓ Ativo                              │
│                                                            │
│ 156 runs total · 42 ativos · 89 concluídos · 25 cancelados │
│ · 0 falhados (últimas 24h)                                 │
└────────────────────────────────────────────────────────────┘
```

Contagens vêm de endpoint dedicado:
```
GET /api/flows/{id}/stats
→ { total, active, completed, cancelled, failed, last_24h_failed }
```

Implementar como SELECT COUNT GROUP BY status. Sem agregação histórica.

## 10. Polling vs SSE

- MVP: SWR polling 10s lista + 5s detalhe ativo
- v2: server-sent events em `/api/flows/runs/{id}/stream` pra debug em tempo real

Polling é suficiente — runs raramente avançam mais de 1x por minuto em produção (cadência humana de WA).

## 11. Empty states

- Lista vazia: "Esse flow ainda não foi executado. [Iniciar pra teste →]" botão que faz manual run pra 1 lead específico
- Sem leads no workspace: "Importe leads primeiro" link pro `/app/leads`
- Detalhe step ainda não chegou: skeleton + "Aguardando próximo step..."

## 12. Mobile

- Lista: linhas viram cards verticais
- Detalhe: tabs em vez de duas colunas (Timeline | Overlay)
- Modal step: full-screen sheet

## 13. Acessibilidade

- Status pills têm cor + ícone (não só cor)
- Timeline tem aria-labels "Step 3 de 7: Send WhatsApp, completed"
- Keyboard: ↑/↓ navega steps, enter abre modal, esc fecha

## 14. Critérios de aceite

- [ ] Lista `/app/flows/[id]/runs` mostra runs com filtros funcionais
- [ ] Detalhe `[run_id]` mostra timeline + overlay sincronizados
- [ ] Polling atualiza node atual em ≤10s sem refresh manual
- [ ] Step modal mostra payload (incluindo rendered template e provider_message_id)
- [ ] Botão Cancelar funciona em runs ativos
- [ ] Failed runs mostram erro + opção retry
- [ ] Tab "Runs" no editor mostra mesma lista embedded
- [ ] Stats header tem contadores certos (test com seed de runs em diferentes status)

## 15. Não coberto

- Métricas agregadas históricas (heatmap, funil de conversão por node)
- Dashboard cross-flow ("top 5 flows com mais cancelamentos")
- Export CSV de runs
- Alertas por threshold (>X% failed → notificação)
- Replay/simulação de flow contra dataset
- Edit do flow inline a partir do step (já tem botão "Editor" no header)
- Logs raw do engine acessíveis na UI (acesso via Railway logs por enquanto)
