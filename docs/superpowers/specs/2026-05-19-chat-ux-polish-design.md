# Chat UX Polish — Design

**Status:** specced — pending plan

**Goal:** Bater paridade visual com Chatwoot / WhatsApp Web no Inbox do SDR através de 5 melhorias frontend-only — sem novos endpoints, sem mudança de modelo.

**Arquitetura:** Frontend Next.js / React. Refactor da view de conversa (`/app/inbox/[id]`) em componentes pequenos, hooks de atalhos + auto-scroll, render de status delivery a partir do `MessageStatus` existente.

**Tech:** React 19, TypeScript, Tailwind v4. Reusa DS Instrumento.

---

## Problema

Print atual do Inbox mostra:
- Header da conversa só com número (`5511982956611`), sem nome do lead, sem avatar
- Mensagens sem indicador de leitura (só `✓` genérico)
- Sem agrupamento por dia — mensagens corridas em um blob
- Não scrolla automaticamente quando chega mensagem nova
- Zero atalhos — closer precisa clicar pra tudo

Closer abre 20+ conversas por dia. Cada atrito custa. Concorrentes (Chatwoot, ManyChat, Salesbot) entregam UX de chat por padrão.

## Escopo

### In scope

1. **Header rico da conversa** (`ConversationHeader.tsx`)
   - Avatar circular: inicial do `lead.nome` se sem foto; usar `profile_pic_url` quando disponível (campo a adicionar opcional)
   - Linha 1: `lead.nome` em destaque
   - Linha 2: status pill do lead (`responded` / `won` / etc) + telefone formatado (`(11) 98295-6611`)
   - Linha 3 (opcional): "evolution · ativo" como subtle subtitle
   - Action button no canto direito: "Abrir Lead →" (já existe na rail mas duplicar no header agiliza)

2. **Status delivery distinguível** (`MessageBubble.tsx`)
   - Mensagens outbound mostram ícone por status:
     - `queued` / `sent` → `✓` cinza
     - `delivered` → `✓✓` cinza
     - `read` → `✓✓` azul (var `--accent`)
     - `failed` → `!` em terracota com tooltip do erro
   - Componente novo: `MessageStatusIcon` (~15 linhas)

3. **Agrupamento temporal** (`DayDivider.tsx`)
   - Render sticky chip horizontal centralizado: "Hoje", "Ontem", "ddd dd/MM" (Intl.DateTimeFormat pt-BR)
   - Insere divider quando dia da mensagem N ≠ dia da mensagem N-1
   - Lógica em `useGroupedMessages(messages)` hook

4. **Auto-scroll para o fim**
   - `useAutoScroll(ref, deps)` hook: faz `scrollIntoView({behavior: "smooth", block: "end"})` quando `deps` mudam
   - Trigger: ao montar conversa, ao chegar msg nova, ao enviar
   - Edge case: se user scrolla pra cima manualmente, **não** auto-scrolla (detecta com `scrollTop + clientHeight < scrollHeight - threshold`). Mostra botão flutuante "↓ N novas mensagens" quando há novas e user está scrollando histórico

5. **Atalhos de teclado** (`useInboxShortcuts` hook)
   - `J` / `K` (ou `↓` / `↑`): navega conversas na lista (próxima / anterior)
   - `Enter` no composer: envia mensagem (já provavelmente é assim, validar)
   - `Shift+Enter` no composer: quebra linha
   - `Cmd+K` (ou `Ctrl+K`): foca search da lista
   - `Esc`: volta pro `/app/inbox` (limpa seleção de conversa) ou fecha modal se aberto
   - `1` / `2` / `3` / `4`: alterna filtro (Todas / Não lidas / Respondidas / Ganho)
   - Mostra cheat sheet com `?` (modal lista atalhos)

### Out of scope

- Foto de perfil real do WhatsApp (`profile_pic_url` do Evolution) — adiciona como coluna `Lead.profile_pic_url` opcional, populado pelo `EvolutionAdapter.fetch_profile()` em PR futuro
- Mensagens reagidas / threadeds / forwarded — vem no spec de reply quotado e copilot
- Drag-and-drop reorder de conversas
- Notificação desktop (push) quando msg nova chega

## Modelo de dados

Sem mudanças. Tudo deriva do existente:
- `Lead.nome` (já existe)
- `OutreachMessage.status` (já existe — `queued`/`sent`/`delivered`/`read`/`failed`)
- `ConversationMessage.timestamp` (já existe)
- Status do lead vem de `Lead.status` enum

Aditivo opcional (não-bloqueante):
```python
class Lead(Base):
    ...
    profile_pic_url: Column(String(512), nullable=True)  # populado depois
```

## Componentes (frontend/src/components/inbox/)

```
ConversationHeader.tsx         (novo)
MessageBubble.tsx              (modificar — adicionar StatusIcon)
MessageStatusIcon.tsx          (novo)
DayDivider.tsx                 (novo)
ConversationView.tsx           (modificar — usar useGroupedMessages + useAutoScroll)
ScrollToBottomFab.tsx          (novo — botão flutuante "↓ N novas")
ShortcutsModal.tsx             (novo — exibido com `?`)
```

Hooks (frontend/src/components/inbox/):
```
useGroupedMessages.ts          (novo — agrupa msgs por dia)
useAutoScroll.ts               (novo — gerencia scroll bottom + detecta user scroll)
useInboxShortcuts.ts           (novo — keybindings globais do inbox)
```

## UX detalhes

### Header rico

```
┌─────────────────────────────────────────────────┐
│ [AC]  Angelo Cerqueira              Abrir Lead →│
│       responded · (11) 98295-6611               │
└─────────────────────────────────────────────────┘
```

- Avatar 40px, fundo `bg-accent-soft`, texto `text-accent`, font-semibold
- Quando `lead.profile_pic_url` existe, `<img>` no lugar da inicial
- Status pill reusa `<StatusPill>` do DS

### Status delivery

```
Outbound bubble:
  Texto da mensagem
                       16:46  ✓✓     ← cinza (delivered)
  Texto da mensagem
                       16:46  ✓✓     ← accent (read)
```

### Day divider

```
─────── Hoje ───────
[mensagens do dia]
─────── Ontem ──────
[mensagens de ontem]
─────── ter 13/05 ──
[mensagens mais antigas]
```

### Auto-scroll FAB

```
                              ┌──────────────┐
                              │ ↓ 3 mensagens│
                              └──────────────┘
[composer]
```

Aparece quando `user_scrolled_up && new_messages_arrived`. Clica → scrolla pro fim.

### Atalhos

- Implementação: `useEffect` global em `/app/inbox/layout.tsx` que registra listener no document
- Cleanup ao sair da rota
- Ignora atalhos quando foco está em `<input>` ou `<textarea>` (com exceção do Enter no composer)

## Edge cases

| Cenário | Comportamento |
|---|---|
| Lead sem nome (campo vazio) | Avatar com `?`, header mostra `+phone` formatado |
| Mensagem futura (msg.timestamp > now por clock skew) | Mostra timestamp normal mas agrupa em "Hoje" |
| Lista vazia, user pressiona J/K | No-op |
| User está digitando no composer + pressiona `1`-`4` | Atalho ignorado (foco em textarea) |
| Histórico muito longo (1000+ msgs) | Virtualizar? Não no MVP — deixar render todas. Reavaliar quando aparecer slowness |
| Mensagem com timestamp inválido | Agrupa em "Sem data" como fallback |

## Decisões tomadas

- **`Cmd+K` em vez de `/`** — `/` é reservado pra slash commands de templates (spec separado)
- **Atalhos em desktop apenas** — mobile já tem boa UX touch, atalhos não fazem sentido
- **Day divider em pt-BR sempre** — não localizar em outras línguas; produto é pt-BR
- **Auto-scroll com smooth scroll** — UX mais suave; única exceção é quando histórico tem 500+ msgs (skip smooth, instant)
- **Cheat sheet com `?`** — padrão da indústria (Linear, Notion, Slack)

## Open questions

- Onde mostrar status do erro detalhado quando msg falha? Tooltip no `!` é discoverable mas hidden — vale ter uma linha "Falha ao enviar — clique pra ver" abaixo da bolha? **Proposta:** tooltip + entry no log de auditoria do lead (rail direita)

## Tamanho estimado

S (1-2 dias). Sem backend. Test plan: visual regressions + unit dos hooks.

## Referências

- WhatsApp Web — status delivery icons
- Chatwoot conversation header + composer
- Linear keyboard shortcuts (modal `?`)
- DS Instrumento — `components/ui/StatusPill`
