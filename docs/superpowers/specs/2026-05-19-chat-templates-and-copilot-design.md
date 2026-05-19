# Chat — Templates + Copilot — Design

**Status:** specced — pending plan

**Goal:** Closer responde 5-10x mais rápido. Duas alavancas combinadas:
- **Templates**: respostas salvas com variáveis (`{{nome}}`, `{{nicho}}`) acessadas por slash command no composer
- **Copilot**: sidebar IA gera 2-3 sugestões de resposta contextuais ao histórico + lead enrichment + LP, com one-click actions ("Mandar LP", "Agendar call", "Marcar ganho")

Combinados num spec porque copilot reusa templates como building block ("AI sugere usar template X") e ambos vivem no mesmo container UI (composer + sidebar).

**Arquitetura:** Backend ganha tabela `templates` + endpoints CRUD + endpoint `suggest-reply` que prompta LLM com contexto. Frontend ganha slash command no composer (autocomplete dropdown) + nova coluna direita (sidebar copilot) que substitui ou complementa a rail atual.

**Tech:** LLM via httpx (mesmo padrão de `generator.py`), Jinja2 ou string.Template pra variáveis, novas migrations.

---

## Problema

**Templates:**
- Closer manda mensagens repetitivas: "Bom dia, vi seu interesse em X, posso te ajudar?", "Segue a proposta em anexo", "Tem disponibilidade quinta às 14h?"
- Hoje cada msg é digitada do zero — tempo perdido + inconsistência de tom
- Concorrentes (Chatwoot, Salesbot, ManyChat) entregam canned responses por padrão

**Copilot:**
- Closer abre uma conversa e precisa reconstituir contexto: ler histórico + olhar score do lead + ver se já mandou LP + decidir próxima ação
- LLM com todo esse contexto pode sugerir 2-3 respostas + qual ação tomar — closer só clica
- Diferencial vs ferramentas de chat genéricas: nosso DB tem lead enrichment (CNPJ, nicho, sócios), LP gerada, score, histórico de outreach — context riquíssimo

## Escopo

### In scope

**Templates:**
1. Modelo + CRUD endpoints
2. Slash command no composer (`/` abre dropdown)
3. Substituição de variáveis ao inserir
4. Contador de uso por template
5. Seed inicial com 5-6 templates default (saudação, agendamento, LP, follow-up, proposta, closing)

**Copilot:**
6. Endpoint `suggest-reply` com prompt enriquecido + cache
7. Sidebar UI com 2-3 sugestões + 3 one-click actions
8. Botão "Pedir sugestão" pra trigger manual; opção de auto-trigger ao abrir conversa
9. Estado: loading, error, success
10. Botão "Refinar" — segunda passada do LLM com instrução tipo "mais direto" / "mais formal"

### Out of scope

- Templates compartilhados entre workspaces (single-tenant hoje)
- Versionamento de templates
- A/B testing entre sugestões
- Agente totalmente autônomo (auto-responder sem closer)
- Multi-turn negotiation pelo copilot
- Templates com mídia (só texto no MVP)
- Internacionalização de templates (pt-BR only)

## Modelo de dados

### Nova tabela `templates`

```python
class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, default=1, index=True)
    slug = Column(String(60), nullable=False)         # ex: "saudacao", "proposta"
    title = Column(String(120), nullable=False)
    body = Column(Text, nullable=False)               # com {{vars}}
    variables = Column(JSONB, default=list)
    # ex: [{"key": "nome", "label": "Nome do lead", "default_from": "lead.nome"}, ...]
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("workspace_id", "slug"),)
```

Variáveis suportadas (resolvidas server-side):
- `{{nome}}` — `lead.nome`
- `{{primeiro_nome}}` — primeiro token de `lead.nome`
- `{{nicho}}` — `lead.nicho`
- `{{cidade}}` — `lead.cidade`
- `{{lp_url}}` — URL pública da LP gerada do lead (se houver)
- `{{seu_nome}}` — `WorkspaceProfile.your_name`
- `{{negocio}}` — `WorkspaceProfile.business_name`

### Seed inicial

```python
# alembic data migration (ou seed script)
DEFAULT_TEMPLATES = [
    {"slug": "saudacao", "title": "Saudação inicial",
     "body": "Oi {{primeiro_nome}}, tudo bem? Aqui é o {{seu_nome}} do {{negocio}}. Vi seu negócio em {{cidade}} e queria te mostrar uma forma de aparecer mais no Google. Posso te explicar em 2min?"},
    {"slug": "proposta-lp", "title": "Mandar LP",
     "body": "Fiz um exemplo pra você ver como ficaria: {{lp_url}}\n\nCabe um papo rápido pra te explicar?"},
    {"slug": "agendamento", "title": "Sugerir horário",
     "body": "Top! Tem disponibilidade quinta às 14h ou sexta às 10h?"},
    {"slug": "followup-48h", "title": "Follow-up 48h",
     "body": "Oi {{primeiro_nome}}, viu o exemplo que mandei? Queria saber sua opinião!"},
    {"slug": "fechamento", "title": "Fechamento",
     "body": "Beleza {{primeiro_nome}}! Pra fechar precisamos só do CNPJ e do email — pode me passar?"},
    {"slug": "perdido-followup", "title": "Tentativa final",
     "body": "Imagino que esteja corrido — se não fizer sentido pra você, me avisa, sem problema. Caso queira tentar outra hora, é só responder aqui."},
]
```

## Backend

### Endpoints templates

```python
# backend/app/routers/templates.py

@router.get("/api/templates")
def list_templates(...): ...

@router.post("/api/templates")
def create_template(payload: TemplateIn, ...): ...

@router.get("/api/templates/{id}")
def get_template(id: int, ...): ...

@router.put("/api/templates/{id}")
def update_template(id: int, payload: TemplateIn, ...): ...

@router.delete("/api/templates/{id}")
def delete_template(id: int, ...): ...

@router.post("/api/templates/{id}/render")
def render_template(id: int, payload: RenderIn, ...):
    """Renderiza template substituindo {{vars}} com info do lead.

    Body: { lead_id: int }
    Retorna: { body: str, variables_resolved: dict }
    """
    template = ...
    lead = db.query(Lead).filter_by(id=payload.lead_id).first()
    profile = db.query(WorkspaceProfile).first()
    ctx = {
        "nome": lead.nome,
        "primeiro_nome": lead.nome.split()[0] if lead.nome else "",
        "nicho": lead.nicho or "",
        "cidade": lead.cidade or "",
        "lp_url": _lp_url(lead),
        "seu_nome": profile.your_name,
        "negocio": profile.business_name,
    }
    rendered = _render(template.body, ctx)
    template.usage_count += 1
    db.commit()
    return {"body": rendered, "variables_resolved": ctx}

def _render(body: str, ctx: dict) -> str:
    """{{var}} substitution. Vars não resolvidas viram `[VAR]` pra evidenciar gap."""
    import re
    return re.sub(r"\{\{(\w+)\}\}", lambda m: ctx.get(m.group(1), f"[{m.group(1).upper()}]"), body)
```

### Endpoint copilot

```python
@router.post("/api/conversations/{id}/suggest-reply")
def suggest_reply(id: int, payload: SuggestIn, ...):
    """Gera 2-3 sugestões de resposta contextual + next-best-action.

    Body: { tone?: "formal" | "direto" | "casual", refine?: str }
    Retorna: { suggestions: [...], next_actions: [...], context_summary: str }
    """
    conv = ...
    lead = db.query(Lead).filter_by(id=conv.lead_id).first()
    last_msgs = db.query(ConversationMessage).filter_by(conversation_id=id).order_by(timestamp.desc()).limit(10).all()
    lp = db.query(LandingPage).filter_by(lead_id=lead.id).order_by(version.desc()).first()
    templates = db.query(Template).filter_by(workspace_id=ws).all()

    prompt = _build_prompt(lead, last_msgs, lp, templates, payload.tone, payload.refine)
    resp = _call_llm(prompt)
    parsed = _parse_llm_response(resp)
    return parsed

class SuggestionsOut(BaseModel):
    suggestions: list[Suggestion]  # 2-3 strings
    next_actions: list[Action]      # ex: [{ "kind": "send_lp", "label": "Mandar LP" }]
    context_summary: str            # "Lead perguntou sobre preço; ainda não viu LP"
```

Prompt schema (estruturado, força JSON output):

```
Você é um assistente de vendas pra um SDR (Sales Development Rep) brasileiro.

CONTEXTO DO LEAD:
- Nome: {nome}
- Negócio: {nicho} em {cidade}
- Score: {score} (0-100, maior = mais oportunidade)
- Tem site: {tem_site}, qualidade: {pontos_fracos}
- CNPJ: {cnpj} ({razao_social}, porte {porte})

HISTÓRICO RECENTE (mais novo primeiro):
[lead] Quanto custa?
[closer] Vai depender do escopo. Que tal um papo rápido?
[lead] Pode ser. Tem horário amanhã?

TEMPLATES DISPONÍVEIS:
- saudacao: "Oi {{primeiro_nome}}, tudo bem?..."
- agendamento: "Top! Tem disponibilidade..."

TAREFA:
Gere 2-3 sugestões de resposta curtas (≤200 chars cada), em pt-BR, tom {tone}.
Também sugira até 3 next-best-actions estruturadas.

Saída em JSON estrito:
{
  "suggestions": ["...", "...", "..."],
  "next_actions": [
    {"kind": "send_template", "template_slug": "agendamento", "label": "Sugerir horário"},
    {"kind": "send_lp", "label": "Mandar LP", "lp_url": "..."},
    {"kind": "mark_status", "to_status": "in_call", "label": "Marcar como em call"}
  ],
  "context_summary": "Lead aceitou conversar e pediu horário pra amanhã."
}
```

**Cache:**
- Hash do contexto (last_msgs + lead.updated_at + lp.version) → cache 2min
- Invalida automaticamente quando msg nova chega (via realtime spec)

### `next_action.kind` enum

| Kind | Frontend behavior |
|---|---|
| `send_template` | Carrega `template_slug` no composer (renderizado) — closer revisa e envia |
| `send_lp` | Insere `lp_url` no composer + texto curto auto |
| `mark_status` | PATCH lead status com confirm dialog |
| `schedule_followup` | Abre modal com date picker, salva como reminder (futuro — pode ser stubbed agora) |
| `request_info` | Insere pergunta padronizada no composer (ex: "Me passa seu CNPJ?") |

## Frontend

### Slash command no composer

Pressionar `/` no composer abre dropdown ancorado:

```
[Mensagem... /sa                                  ][Enviar]
              ┌────────────────────────────────┐
              │ /saudacao    Saudação inicial  │  ← filtro fuzzy
              │ /agendamento Sugerir horário   │
              │ /proposta-lp Mandar LP         │
              └────────────────────────────────┘
```

- Setas ↑/↓ navegam, Enter insere
- Esc fecha sem inserir
- Ao escolher: chama `POST /api/templates/{id}/render?lead_id=X` → body renderizado preenche o textarea
- Closer ainda revisa antes de Enviar
- Variáveis não resolvidas viram `[NICHO]` (caps brackets) — evidência clara de gap

Componente:
```
ComposerWithSlashCommands.tsx
  → SlashCommandMenu.tsx (dropdown ancorado, fuzzy filter)
  → useTemplateRender(template_id, lead_id) hook
```

### Sidebar copilot

Substitui ou complementa a rail direita atual (que mostra info do lead). Layout:

```
┌─ COPILOT ─────────────────────────┐
│                                    │
│ Lead aceitou conversar e pediu     │  ← context_summary
│ horário pra amanhã.                │
│                                    │
│ ─── Sugestões ────                  │
│                                    │
│ ⚡ Top! Tenho 14h ou 16h.          │  ← suggestion 1
│   [Usar]                           │
│                                    │
│ ⚡ Beleza, amanhã 15h cabe pra você?│  ← suggestion 2
│   [Usar]                           │
│                                    │
│ ⚡ Quinta às 10h ou sexta às 14?   │  ← suggestion 3
│   [Usar]                           │
│                                    │
│ [↻ Refinar]   [⚙ Tom: direto ▾]   │
│                                    │
│ ─── Próximas ações ────             │
│                                    │
│ ▸ Sugerir horário (template)       │
│ ▸ Mandar LP                        │
│ ▸ Marcar como "em call"            │
│                                    │
└────────────────────────────────────┘
```

- "Usar" preenche o composer com a sugestão (não envia direto — closer revisa)
- "Refinar" reabre LLM com instrução adicional ("mais direto", "mais formal", "mais curto")
- Selector de tom: dropdown 3 opções
- "Próximas ações" são clicáveis e executam o `kind` correspondente

### Toggle copilot

Não queremos copilot empurrado goela abaixo. Toggle no header da conversa:

```
[AC] Angelo Cerqueira     [○ Copilot]  Abrir Lead →
```

- Off por default no MVP
- User liga manualmente; preferência salva em `localStorage`
- Quando ligado, busca sugestão automática ao abrir conversa nova
- Quando desligado, sidebar mostra a rail original (lead info)

## Edge cases

| Cenário | Comportamento |
|---|---|
| Template com variável não resolvível (`{{cnpj}}` mas lead sem CNPJ) | Substitui por `[CNPJ]` em caps; closer vê e edita |
| Slug duplicado no create | 422 com "slug já existe" |
| Slug com chars inválidos | Sanitizar pra `^[a-z0-9-]+$`; ou 422 |
| Slash command com 0 matches | Dropdown vazio com "Nenhum template — criar?" link |
| LLM offline / timeout | Fallback: sidebar mostra apenas next_actions baseadas em heurística simples (sem suggestions); banner "Sugestões IA indisponíveis" |
| LLM responde JSON malformado | Retry 1x; se ainda falha, suggestions=[] + log warning |
| Sugestão gera texto inadequado (filter) | Sem moderation no MVP; closer sempre revisa antes de enviar |
| Histórico muito longo (200 msgs) | Limita a últimas 10 msgs no prompt — balance contexto/custo |
| Lead com dados sensíveis (CPF, dados bancários no histórico) | Sem redação no MVP; LLM API call envia tudo. **Privacidade:** documentar no Settings que histórico vai pro LLM provider |
| Custo do LLM por conversa | Tracking: emitir métrica `copilot.suggestion_generated` com tokens; permite estimar custo mensal |
| Templates com URL/markdown | Body é texto puro WhatsApp; se template tem markdown, vira plain text |

## Decisões tomadas

- **Templates como base do copilot** — copilot sugere `next_actions` que apontam pra templates existentes; sem duplicar lógica de geração
- **Variáveis com `{{key}}` syntax** — padrão da indústria (Liquid-like simples)
- **Vars não resolvidas viram `[KEY]`** em caps em vez de string vazia — closer percebe e corrige; vazio cria msg estranha
- **Copilot opt-in com toggle** — não queremos surpreender closer com sugestão automática toda conversa (custo + intrusivo)
- **Cache 2min do copilot** — mensagens novas invalidam; refinar não usa cache
- **JSON estrito do LLM** — usar mode `json_object` quando suportado (OpenAI/Anthropic) pra evitar parsing fragility
- **Seed de templates default** — closer começa com 6 templates úteis; pode editar/deletar
- **Sem template com mídia no MVP** — texto-only; mídia + caption fica pra futuro

## Open questions

- **Onde mostrar contador de uso do template?** Lista de templates no Settings? **Proposta:** sim, coluna "Usado X vezes" + ordena por uso desc
- **Permitir snippets pessoais (não compartilhados)?** Multi-user no futuro precisa disso. **Proposta:** schema já comporta `created_by_user_id` future-proof; MVP é workspace-shared
- **Pré-aquecer copilot** ao abrir conversa, mesmo com toggle off, pra ter resposta instant ao ligar? **Proposta:** não — economia de tokens; usuário aceita 2s loading na 1ª request
- **Templates podem ter "sub-templates"** (composição)? Ex: `{{template:saudacao}} {{template:agendamento}}` — **Proposta:** não no MVP, YAGNI

## Tamanho estimado

L (5-7 dias). Backend: 2 migrations + 6 endpoints + LLM integration + cache. Frontend: dropdown slash command + sidebar copilot + toggle + tone selector. Tests: render variables, slug uniqueness, LLM mocking, fallback behavior.

## Referências

- `backend/app/pipeline/generator.py` — pattern de LLM call via httpx
- Linear, Slack, Chatwoot — slash commands UX
- Notion AI / Linear Insights — sidebar copilot pattern
- OpenAI / Anthropic — JSON output mode
