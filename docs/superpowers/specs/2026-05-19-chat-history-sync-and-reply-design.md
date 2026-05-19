# Chat — Sync de histórico + Reply quotado — Design

**Status:** specced — pending plan

**Goal:** Ao conectar uma instance Evolution, importar chats e mensagens existentes pro DB do SDR. Resolve o gap visual onde Evolution Manager mostra histórico e SDR está vazio. Inclui suporte a reply quotado (mensagens citadas) — feature paralela porque o sync precisa preservar essa informação.

**Arquitetura:** Background job idempotente que pagina `findChats` + `findMessages` da Evolution, normaliza via parser existente, cria leads órfãos (reusa `create_inbound_lead`), cria conversations e messages com dedupe por `provider_message_id`. Para reply quotado, expande modelo de `ConversationMessage` com `quoted_message_id` FK auto-referencial, e parser extrai `contextInfo.quotedMessage` do payload.

**Tech:** Background task FastAPI, SSE pra progresso, paginação Evolution `?page=&offset=`, novo job type.

---

## Problema

**Sync de histórico:**
- Evolution Manager mostra contatos e chats que já existiam quando o SDR conectou
- Nosso DB só captura mensagens que chegam via webhook DEPOIS da conexão
- Closer perde contexto histórico — sabe que falou com lead X há 2 semanas mas não vê
- Cada cliente que se conecta com instance "antiga" começa o produto sem dado

**Reply quotado:**
- WhatsApp permite "responder" mensagem específica — fica citada acima da resposta
- Evolution entrega isso em `message.{type}.contextInfo.quotedMessage`
- Hoje ignoramos — closer perde a referência ("respondi a quê?")
- Sem isso, conversa com muito ping-pong vira ilegível

## Escopo

### In scope

**Sync:**
1. Endpoint `POST /api/workspace/integrations/evolution/sync-history` — dispara job
2. Background job idempotente:
   - `findChats` paginado (page=1..N, limite por workspace = 1000 chats)
   - Pra cada chat, `findMessages` (últimos 30 dias por padrão)
   - Dedup por `provider_message_id`
   - Auto-cria leads órfãos pra chats sem lead match (reusa `create_inbound_lead`)
   - Cria conversations + messages
3. Progresso via SSE: `chats_total`, `chats_processed`, `messages_imported`, `leads_created`
4. UI: botão "Importar histórico" no Settings com modal de progresso
5. Window configurável: 7 / 30 / 90 / 180 dias

**Reply quotado:**
1. Migration: adiciona `quoted_message_id` (FK self-referencial nullable) em `conversation_messages`
2. Adapter parser extrai `quotedMessage.key.id` (e snapshot do body como fallback)
3. Handler resolve `provider_message_id → ConversationMessage.id` no insert
4. UI: quote box renderizado acima da bolha

### Out of scope

- Sync incremental contínuo (pull periódico) — webhook resolve isso pra eventos novos
- Mídia hot-download durante sync — só metadata; URL signed do Evolution expira mas marcamos `media_url_evolution` + `media_expired_at`; download on-demand via outro spec
- Sync de grupos — só 1:1 chats no MVP
- Sync de reactions, polls, location, contact cards
- Reply em mensagens fora do range importado — quote box mostra `(mensagem fora do histórico)` fallback

## Modelo de dados

### `ConversationMessage` (alterações)

```python
class ConversationMessage(Base):
    ...
    quoted_message_id: Column(Integer, ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    quoted_message = relationship("ConversationMessage", remote_side=[id], foreign_keys=[quoted_message_id])

    # Fallback quando msg citada não está no DB (sync parcial, msg muito antiga)
    quoted_snapshot: Column(JSONB, nullable=True)
    # ex: {"body": "...", "from_phone": "...", "timestamp": "..."}
```

Migration:
- `add_column quoted_message_id` (nullable int FK)
- `add_column quoted_snapshot` (jsonb)
- Index em `(quoted_message_id)` pra lookup reverso (futuro: "ver todas as respostas a essa msg")

### Novo job type

```python
# app/models.py — Job.kind enum amplia
JOB_KINDS = ("scrape", "enrich", "generate", "outreach", "classify", "sync_whatsapp_history")
```

`Job.params` carrega:
```json
{
  "provider": "evolution",
  "instance": "sdr",
  "window_days": 30,
  "include_groups": false
}
```

`Job.result_summary` ao fim:
```json
{
  "chats_total": 42,
  "chats_processed": 42,
  "messages_imported": 1283,
  "messages_skipped_duplicate": 41,
  "leads_created": 18,
  "errors": []
}
```

## Backend

### Endpoint

```python
# backend/app/routers/workspace_settings.py
@router.post("/integrations/evolution/sync-history")
def start_history_sync(payload: SyncHistoryIn, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    # Cria Job + dispara background task (mesmo pattern de outros pipelines)
    job = Job(kind="sync_whatsapp_history", status="pending", params=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    _spawn_job_thread(_run_sync_history, job.id, ws)  # reusa _spawn helper do pipeline.py
    return {"job_id": job.id}

class SyncHistoryIn(BaseModel):
    window_days: int = Field(default=30, ge=1, le=365)
    include_groups: bool = False
```

### Job runner

```python
# backend/app/pipeline/sync_history.py
def _run_sync_history(job_id: int, workspace_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).get(job_id)
        job.status = "running"; db.commit()
        emit_event(job_id, "started", {})

        adapter = get_provider(db, workspace_id=workspace_id, provider="evolution")
        window_days = job.params["window_days"]
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        chats = adapter.fetch_chats()  # GET /chat/findChats/{instance}
        summary = {"chats_total": len(chats), "chats_processed": 0,
                   "messages_imported": 0, "messages_skipped_duplicate": 0,
                   "leads_created": 0, "errors": []}

        for chat in chats:
            try:
                if chat.is_group and not job.params["include_groups"]:
                    continue
                _import_chat(db, workspace_id, chat, cutoff, summary)
                summary["chats_processed"] += 1
                emit_event(job_id, "progress", {"current": summary["chats_processed"], "total": summary["chats_total"]})
            except Exception as exc:
                summary["errors"].append({"chat_id": chat.id, "error": str(exc)[:200]})
                logger.exception("sync_history.chat_failed chat=%s", chat.id)

        job.status = "done"
        job.result_summary = summary
        db.commit()
        emit_event(job_id, "done", summary)
    except Exception as exc:
        job.status = "failed"; job.error_message = str(exc)[:500]
        db.commit(); emit_event(job_id, "error", {"message": str(exc)})
    finally:
        db.close()


def _import_chat(db, workspace_id, chat, cutoff, summary):
    """Importa mensagens de 1 chat. Idempotent — pula duplicatas."""
    # Resolve ou cria lead
    lead = find_lead_by_phone(db, workspace_id, normalized_phone=chat.phone)
    if lead is None:
        lead = create_inbound_lead(
            db, workspace_id=workspace_id,
            normalized_phone=chat.phone,
            push_name=chat.name,
            provider="evolution",
        )
        summary["leads_created"] += 1

    # Cria/recupera conversation
    conv = get_or_create_conversation(
        db, workspace_id=workspace_id, lead_id=lead.id,
        provider="evolution", provider_chat_id=chat.provider_chat_id,
        phone=chat.phone,
    )

    # Pagina mensagens
    page = 1
    while True:
        msgs = adapter.fetch_messages(chat_id=chat.provider_chat_id, page=page, limit=100, since=cutoff)
        if not msgs:
            break
        for raw_msg in msgs:
            parsed = adapter.parse_message(raw_msg)  # mesma normalização do webhook
            if _message_exists(db, parsed.provider_message_id):
                summary["messages_skipped_duplicate"] += 1
                continue
            _append_with_quoted(db, conv.id, parsed)
            summary["messages_imported"] += 1
        page += 1
```

### EvolutionAdapter — métodos novos

```python
def fetch_chats(self) -> list[ChatSummary]:
    """GET /chat/findChats/{instance}"""
    r = httpx.get(self._url(f"chat/findChats/{self.instance}"), ...)
    return [self._parse_chat(c) for c in r.json()]

def fetch_messages(self, *, chat_id: str, page: int = 1, limit: int = 100, since: datetime | None = None) -> list[dict]:
    """GET /chat/findMessages/{instance} — pagina + filtro por chat."""
    body = {"where": {"key": {"remoteJid": chat_id}}, "page": page, "offset": limit}
    if since:
        body["where"]["messageTimestamp"] = {"gte": int(since.timestamp())}
    r = httpx.post(self._url(f"chat/findMessages/{self.instance}"), json=body, ...)
    return r.json().get("messages", {}).get("records", [])

def parse_message(self, raw: dict) -> InboundMessage:
    """Normaliza msg de /findMessages no mesmo shape do webhook."""
    # Reusa lógica de parse_webhook
```

### Reply quotado

**Parser** — adapter extrai do payload:

```python
def parse_webhook(self, raw):
    ...
    msg = data.get("message") or {}
    quoted = self._extract_quoted(msg)
    return [InboundMessage(..., quoted=quoted)]

def _extract_quoted(self, msg: dict) -> QuotedMessage | None:
    """Procura contextInfo.quotedMessage em qualquer message type."""
    for key in ("conversation", "imageMessage", "audioMessage", "documentMessage", "videoMessage", "extendedTextMessage"):
        ctx = msg.get(key, {}).get("contextInfo") or msg.get("contextInfo", {})  # extendedTextMessage tem no root
        quoted_msg = ctx.get("quotedMessage")
        if quoted_msg:
            return QuotedMessage(
                provider_message_id=ctx.get("stanzaId", ""),
                snapshot={
                    "body": self._extract_body(quoted_msg),
                    "from_phone": parse_chat_id(ctx.get("participant", "")),
                },
            )
    return None
```

Novo type:
```python
@dataclass(frozen=True)
class QuotedMessage:
    provider_message_id: str
    snapshot: dict  # body, from_phone (fallback se msg citada não está no DB)
```

**Handler** — resolve FK ao append:

```python
def append_message(db, *, conversation_id, ..., quoted: QuotedMessage | None = None):
    msg = ConversationMessage(...)
    if quoted:
        quoted_db = db.query(ConversationMessage).filter_by(
            provider_message_id=quoted.provider_message_id
        ).first()
        if quoted_db:
            msg.quoted_message_id = quoted_db.id
        else:
            msg.quoted_snapshot = quoted.snapshot
    db.add(msg); db.flush()
    return msg
```

## Frontend

### UI sync (Settings → Evolution)

Novo bloco no `/app/settings/integracoes/evolution`:

```
┌─ Histórico de Mensagens ──────────────────────┐
│                                                │
│ Importar conversas existentes do Evolution    │
│ pro Inbox do SDR (1ª vez ou re-sync).         │
│                                                │
│ Período: [○ 7 dias  ● 30 dias  ○ 90 dias]    │
│                                                │
│ [ Importar histórico ]                         │
│                                                │
│ Última importação: 13/05 16:23 — 42 chats,   │
│ 1.283 mensagens, 18 leads criados.             │
└────────────────────────────────────────────────┘
```

Clicar abre modal com progress SSE (reusa o pattern do `JobProgress`):
```
Importando histórico...
████████░░░░░░░░░░░░  42%  (18 de 42 chats)
1.114 mensagens importadas  ·  14 leads criados
```

### UI reply quotado

```
┌──────────────────────────────────────┐
│ ▎ Angelo: e o preço da consultoria? │  ← quote box (subtle, com border lateral)
│ Aí vai: R$ 4.500 / mês               │  ← mensagem nova
│                              16:46  ✓│
└──────────────────────────────────────┘
```

Componente: `<QuotedMessagePreview>` recebe `quoted_message_id` (lookup no cache de msgs) ou `quoted_snapshot` (fallback render direto).

Click no quote box → scrolla até a msg original (`scrollIntoView`) com highlight temporário.

## Edge cases

| Cenário | Comportamento |
|---|---|
| Sync inicial enorme (10k+ msgs) | Paginação Evolution + commit batch a cada 100 msgs; SSE progresso evita timeout |
| User dispara 2 syncs simultâneos | Job tem `unique partial index` em `(workspace_id, kind, status IN running,pending)` — 2º retorna 409 com "sync já em andamento" |
| Evolution offline durante sync | Job marca `failed` com `error_message`; user reroda |
| Lead já existe (telefone match) | Reusa, não duplica |
| Conversation já existe com mensagens parciais | Sync popula só msgs com `provider_message_id` desconhecido |
| Reply pra msg fora da janela importada | `quoted_message_id` null + `quoted_snapshot` populado; UI mostra preview com snapshot |
| Reply pra msg deletada (Evolution retorna `protocolMessage`) | Quote snapshot com `body: "Mensagem deletada"` |
| Múltiplos chats com mesmo phone (caso raro) | `to_chat_id(phone)` é determinístico — get_or_create_conversation faz dedupe |
| Grupos misturados na resposta | Filtro `is_group` no parser; se `include_groups=false` (default), pula |
| Sync incluir mensagens MUITO antigas | Janela máx 365 dias hard cap pra não estourar storage |
| Mídia em msgs históricas | URL Evolution expirada; gravar `media_url=null` + `media_url_evolution=<original>` + `media_expired_at=<now>`; UI mostra "Mídia indisponível (histórico)" |

## Decisões tomadas

- **Window default 30 dias** — balance entre contexto útil e storage/tempo
- **`include_groups=false` por default** — produto é SDR 1:1, grupos não fazem parte do escopo
- **Mídia metadata-only no sync** — baixar 1000 mídias custaria muito tempo + storage; user dispara download on-demand se precisar (futuro)
- **Reply quotado dual: FK + snapshot** — FK pra UX rica (scroll, highlight); snapshot pra mensagens fora do range importado
- **Background task em vez de Celery/RQ** — consistente com padrão atual do projeto; migra quando justificar
- **SSE pra progresso** — mesmo pattern dos outros jobs; frontend já sabe consumir

## Open questions

- **Cache findChats** — Evolution v2 caches no DB Postgres dele, retornos relativamente rápidos. Vale cachear nosso lado? **Proposta:** não no MVP, monitorar latência
- **Persistir `last_sync_at` na integration** — pra evitar re-sync redundante? **Proposta:** sim, salvar `EvolutionConfig.last_history_sync_at`; UI mostra "última importação"
- **Re-sync incremental** — chamar `findMessages` só com `since=last_sync_at`? **Proposta:** sim como otimização futura, mas no MVP cada sync re-baixa janela completa (idempotente, custo OK pra 30 dias)
- **Notificação ao fim do sync** — toast? email? **Proposta:** toast no Settings + atualiza counter "última importação"; sem email no MVP

## Tamanho estimado

L (4-5 dias). Backend: migration + 2 adapter methods + parser quoted + job runner + endpoint. Frontend: UI sync no Settings + progress modal + QuotedMessagePreview component. Tests: idempotency, quoted FK resolution, pagination, sync re-run.

## Referências

- Evolution API v2 — `GET /chat/findChats/{instance}`, `POST /chat/findMessages/{instance}`
- `backend/app/routers/pipeline.py` — pattern Job + SSE
- `backend/app/whatsapp/services.py:create_inbound_lead` (já existe, reusa)
- Chatwoot conversation reply UX (quote box clickável)
