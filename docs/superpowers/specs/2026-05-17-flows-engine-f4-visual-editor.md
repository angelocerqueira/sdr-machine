# Flows Engine — F-4 Visual Editor (Frontend) Spec

> **Foundation:** [F-0](2026-05-17-flows-engine-f0-architecture.md) · [F-3](2026-05-17-flows-engine-f3-triggers-api.md)
> **Status:** ready to plan
> **Depende:** F-3 (API CRUD pronta)
> **Stack:** Next.js 16 App Router + React 19 + TypeScript + Tailwind 4 + DS Instrumento

## 1. Objetivo

Editor visual drag-and-drop pra criar/editar Flows definidos em F-0. Usa **`@xyflow/react`** (sucessor maintained do `react-flow-renderer`) com paleta lateral, sidebar de config, validação client-side mirror do server-side (F-1 §11).

## 2. Rotas Next.js

```
frontend/src/app/app/flows/
├── page.tsx                          # GET /api/flows → lista flows (cards)
├── new/page.tsx                      # editor em branco (start node criado auto)
└── [id]/page.tsx                     # editor com flow carregado
```

Acesso: navegação a partir da AppSidebar — novo item "Fluxos" entre "Pipeline" e "Leads".

## 3. Stack libs

```json
{
  "@xyflow/react": "^12.x",       // editor canvas
  "@dnd-kit/core": "existing",    // já no projeto pra Kanban — usa de palette
  "swr": "existing",              // fetch
  "zustand": "^5.0"               // estado local do editor (nodes, edges, dirty)
}
```

Zustand é decisão nova. Justificativa: editor tem ~10 pieces de estado interrelacionado (selectedNode, palette, isDirty, validationErrors, undoStack), `useState` proliferação fica ruim. Zustand é pequeno (1KB), TypeScript-first, sem provider hell.

Se preferir evitar lib nova: usar React 19 `useReducer` com contexto único — equivalente, mais boilerplate.

## 4. Estrutura

```
frontend/src/components/flows/
├── editor/
│   ├── FlowEditor.tsx              # canvas principal — wraps <ReactFlow>
│   ├── FlowEditorToolbar.tsx       # save, validate, undo/redo, version label
│   ├── NodePalette.tsx             # drawer lateral esquerdo — 6 tipos draggable
│   ├── NodeConfigSidebar.tsx       # drawer direito — params do node selecionado
│   ├── FlowValidationBanner.tsx    # banner topo se erros
│   └── nodes/
│       ├── StartNode.tsx           # custom node renderers
│       ├── SendWhatsappNode.tsx
│       ├── SendEmailNode.tsx
│       ├── WaitNode.tsx
│       ├── BranchOnReplyNode.tsx
│       ├── SetStatusNode.tsx
│       └── EndNode.tsx
├── list/
│   ├── FlowsList.tsx               # grid de cards na /app/flows
│   └── FlowCard.tsx                # nome + status + last_run_at + count of active runs
├── store/
│   └── editorStore.ts              # Zustand: nodes, edges, selectedId, isDirty, errors
├── validation.ts                   # mirror de F-1 §11
└── api.ts                          # wrappers de api.ts existente
```

## 5. Layout editor (mobile-first)

```
┌─────────────────────────────────────────────────────────────────┐
│ Topbar: ← Voltar    [Flow Name (editable)]    [Save] [Enable]    │
├─────────┬─────────────────────────────────────┬─────────────────┤
│ Palette │  Canvas (xyflow)                    │ Config sidebar  │
│ (240px) │                                     │ (320px)         │
│         │                                     │                 │
│ Start   │   ┌─────────┐                       │ Selected node:  │
│ Send WA │   │ Start   │                       │ send_whatsapp   │
│ Send Em │   └────┬────┘                       │                 │
│ Wait    │        │                            │ Body: textarea  │
│ Branch  │   ┌────▼──────┐                     │ (Jinja vars)    │
│ SetStat │   │ Send WA   │                     │                 │
│ End     │   └────┬──────┘                     │ Media URL:      │
│         │        │                            │ (optional)      │
│         │   ┌────▼──────┐                     │                 │
│         │   │ Wait 2d   │                     │ [Delete node]   │
│         │   └────┬──────┘                     │                 │
│         │        │                            │                 │
│         │   ┌────▼──────┐                     │                 │
│         │   │ End       │                     │                 │
│         │   └───────────┘                     │                 │
└─────────┴─────────────────────────────────────┴─────────────────┘
```

Mobile (<768px):
- Palette vira bottom sheet (swipe-up)
- Config sidebar vira modal full-screen ao selecionar
- Canvas single-column, pan/zoom touch

## 6. Custom node design

Cada custom node ~180px wide × 80px tall com:
- Icon (lucide-react) + label
- Preview do conteúdo (primeiras 40 chars do body, ou "Aguardar 2d", etc)
- Status pill se em run (executado/pulado/erro)

Cores (DS Instrumento):
- **Start/End:** salvia (terminal)
- **send_whatsapp:** accent blue
- **send_email:** mostarda (diferente do WA pra distinguir canal)
- **wait:** neutral (cinza-azul)
- **branch_on_reply:** terracotta (atenção — branching)
- **set_status:** accent darker

## 7. Estado editor (Zustand)

```ts
// store/editorStore.ts
interface EditorState {
  flowId: number | null
  name: string
  description: string
  triggers: Trigger[]
  nodes: Node[]
  edges: Edge[]
  selectedNodeId: string | null
  selectedEdgeId: string | null
  isDirty: boolean
  validationErrors: string[]
  undoStack: Snapshot[]
  redoStack: Snapshot[]
}

interface EditorActions {
  loadFlow(flow: FlowResponse): void
  addNode(type: NodeType, position: XY): void
  updateNodeParams(id: string, params: Partial<NodeParams>): void
  deleteNode(id: string): void
  connectNodes(source: string, target: string, label: EdgeLabel): void
  deleteEdge(id: string): void
  selectNode(id: string | null): void
  validate(): boolean  // mutates validationErrors
  save(): Promise<void>
  undo(): void
  redo(): void
}
```

Undo/redo: snapshots de `{nodes, edges, triggers, name, description}` no `undoStack` antes de cada mutate. Max 50.

## 8. Validação client-side

`validation.ts` espelha `app/flows/validation.py` (F-1):
- 1 start node
- Edges com refs válidas
- DAG (sem ciclo) — DFS
- Todo path → end — BFS
- branch_on_reply tem 2 edges labeled
- Params válidos por tipo (Pydantic-like com Zod)

Roda **on change** com debounce 300ms, atualiza `validationErrors`. Banner topo mostra "3 problemas — clique pra ver" → modal expandido.

Server-side validation via `POST /api/flows/{id}/validate` é o **autoritativo**. Salvar sempre re-valida no servidor; client é só UX (impede submit óbvio cedo).

## 9. Save flow

```ts
async function save() {
  const valid = validate()
  if (!valid) return // banner já mostra
  const payload = serialize() // FlowConfig
  if (flowId == null) {
    const created = await api.post("/api/flows", payload)
    router.push(`/app/flows/${created.id}`)
  } else {
    await api.put(`/api/flows/${flowId}`, payload)
  }
  set({ isDirty: false })
  toast.success("Flow salvo")
}
```

**Antes de navegar away com dirty=true:** confirm dialog.

## 10. Triggers config

Aba **"Triggers"** na config sidebar (visível quando nenhum node selecionado, mostra config global do flow):

```
┌────────────────────────────────┐
│ Triggers                       │
│                                │
│ [✓] Manual                     │
│ [ ] Auto por status do lead    │
│     De: [+ adicionar status]   │
│     Para: outreach_ready ✕     │
│                                │
│ [ ] Webhook externo            │
│     URL: /api/flows/123/trigger│
│     Secret: ●●●●1234 [Rotacionar]
│                                │
└────────────────────────────────┘
```

Webhook URL é read-only (gerado server-side via endpoint análogo ao P2 webhook-url). Secret rotaciona via `POST /api/workspace/integrations/flows/rotate`.

## 11. Editor list view (/app/flows)

Grid de cards:

```
┌──────────────────────┬──────────────────────┐
│ Prospecção fria      │ Reativação dormentes │
│ ●●●○○ 5 nodes        │ ●●○○○ 3 nodes        │
│ ✓ Ativo · 12 runs    │ ⏸ Pausado            │
│ Última edit: ontem   │ Última edit: 3d      │
└──────────────────────┴──────────────────────┘

[+ Novo flow]
```

Click → editor. Hover → ações (duplicar, exportar JSON, deletar).

## 12. Templating helpers no body editor

Textarea de `send_whatsapp.body` e `send_email.body` mostra autocomplete de variáveis disponíveis:

```
┌─────────────────────────────────────┐
│ Olá {{lead.nome}}, vi seu negócio   │
│ em {{lead.cidade}} no nicho de      │
│ {{lead.nicho}}.                     │
│                                     │
│ {{lead.lp_url}} pode te interessar. │
│                                     │
│ {{workspace.your_name}}             │
└─────────────────────────────────────┘
[Inserir variável ▾]
```

Dropdown lista variáveis disponíveis (vem do schema do F-1 templating §7). Click insere `{{xxx}}` no cursor.

Preview button → render com lead de exemplo (primeiro lead do workspace) na sidebar.

## 13. Testes

```
__tests__/flows/
├── editor.store.test.ts            # mutações Zustand, undo/redo, isDirty
├── editor.validation.test.ts       # ciclo, dangling, branch edges, etc
├── editor.serialize.test.ts        # serialize/deserialize roundtrip
└── components/
    └── FlowsList.test.tsx          # render + ações card
```

E2E (Playwright opcional): criar flow → adicionar 3 nodes → conectar → save → enable.

## 14. A11y / mobile

- Canvas focado com keyboard nav (tab entre nodes; enter abre config)
- Atalhos: `cmd+s` save, `cmd+z/y` undo/redo, `delete` remove selected, `cmd+d` duplicate
- Touch: pinch zoom, pan drag, long-press abre config
- Drag from palette tem fallback tap-then-tap pra accessibility

## 15. Critérios de aceite

- [ ] Lista `/app/flows` mostra flows do workspace
- [ ] Editor `/app/flows/new` cria flow vazio com start node
- [ ] Drag from palette → drop on canvas → node aparece + selecionado
- [ ] Conectar 2 nodes → edge aparece (label="out" default)
- [ ] Click branch_on_reply edge → escolha label out_yes/out_no
- [ ] Sidebar mostra form do node selecionado; mudança atualiza canvas
- [ ] Validação client mostra erros em banner
- [ ] Save POST/PUT /api/flows; recebe 422 → mostra errors do server
- [ ] Enable só permitido se válido
- [ ] Mobile (<768px): palette + config viram bottom sheets
- [ ] Undo/redo 50 steps

## 16. Não coberto

- Variants A/B (v2)
- Sub-flows / composição
- Templates do marketplace (importar fluxos prontos)
- Cópia/import/export JSON via UI (botão "exportar" pode existir; importar via paste é v2)
- Histórico de versões com diff visual
- Comentários em nodes
- Collaborative editing (multi-user)
