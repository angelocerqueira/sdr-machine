# Chat — Realtime + Presence — Design

**Status:** specced — pending plan

**Goal:** Mensagens aparecem em tempo real quando o lead responde (sem refresh / poll lento). Mostrar "digitando…" quando o lead está digitando. Emitir presence outbound pro WhatsApp quando o closer está digitando.

**Arquitetura:** SSE (Server-Sent Events) por conversa, espelhando o padrão já estabelecido em `routers/pipeline.py` (`GET /api/jobs/{id}/stream`). Pub/sub in-memory pra MVP (single-worker Railway), migrável pra Redis quando escalar pra múltiplas réplicas.

**Tech:** FastAPI SSE via `sse-starlette` (já instalado), `EventSource` API no frontend, pub/sub via `dict[int, list[asyncio.Queue]]` in-memory.

---

## Problema

Hoje:
- Conversa list refresca via SWR a cada 5s (`refreshInterval: 5000`) — OK pra "tem novidade?"
- Conversa aberta NÃO refresca em tempo real. Closer precisa fechar/abrir ou recarregar pra ver msg nova
- Sem indicador "digitando…" — Evolution emite `presence.update` no webhook, mas ignoramos
- Closer está digitando: lead não vê "digitando…" → fricção de UX (lead pensa "ele sumiu?")

Concorrentes (Chatwoot, WhatsApp Web, Intercom) entregam realtime + presence por padrão.

## Escopo

### In scope

1. **SSE de eventos por conversa** — endpoint `GET /api/conversations/{id}/stream`
2. **Pub/sub interno** — webhook handler + endpoint outbound emitem eventos; SSE consome
3. **Presence inbound** — webhook `presence.update` (composing, recording, available) → cache TTL → push via SSE
4. **Presence outbound** — composer com debounce emite `sendPresence` no Evolution
5. **Frontend** — hook `useConversationStream` que faz subscribe + dispatch pros SWR caches

### Out of scope

- Pub/sub via Redis (escalar pra multi-worker) — projetar interface trocável, implementar in-memory hoje
- WebSocket bidirecional — SSE é suficiente; outbound vai via HTTP normal
- Mensagens lidas em massa (sync de read receipts retroativo) — fora deste spec
- Indicator "online / offline" do contato — fora; só foco em digitando/gravando

## Backend

### Pub/sub interno (`backend/app/realtime/`)

Estrutura nova:

```python
# backend/app/realtime/bus.py
from asyncio import Queue
from collections import defaultdict

class EventBus:
    """In-memory pub/sub. 1 instance por processo. Single-worker safe."""

    def __init__(self):
        self._subs: dict[str, list[Queue]] = defaultdict(list)

    def subscribe(self, topic: str) -> Queue:
        q = Queue(maxsize=100)
        self._subs[topic].append(q)
        return q

    def unsubscribe(self, topic: str, q: Queue) -> None:
        self._subs[topic].remove(q)
        if not self._subs[topic]:
            del self._subs[topic]

    async def publish(self, topic: str, event: dict) -> None:
        for q in self._subs.get(topic, []):
            try:
                q.put_nowait(event)
            except QueueFull:
                pass  # slow consumer — descarta evento, não bloqueia publisher

bus = EventBus()  # singleton no módulo
```

Topics (string keys):
- `conversation:{id}` — eventos de mensagem nova / status update / presence pra essa conversa
- `workspace:{workspace_id}` — eventos cross-conversation (futuro: novo lead inbound criado)

### SSE endpoint (`backend/app/routers/conversations.py`)

```python
from sse_starlette.sse import EventSourceResponse
from app.realtime.bus import bus

@router.get("/api/conversations/{id}/stream")
async def stream_conversation_events(id: int, request: Request, ...):
    # Auth: validar acesso ao workspace dono dessa conversa
    conversation = db.query(Conversation).filter_by(id=id, workspace_id=ws).first()
    if not conversation:
        raise HTTPException(404)

    topic = f"conversation:{id}"
    q = bus.subscribe(topic)

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await q.get()
                yield {"event": event["type"], "data": json.dumps(event["data"])}
        finally:
            bus.unsubscribe(topic, q)

    return EventSourceResponse(event_gen())
```

Eventos emitidos:
- `message.created` — nova msg inbound ou outbound
- `message.status_changed` — sent → delivered → read
- `presence.updated` — `{state: "composing" | "recording" | "available", expires_at: ...}`

### Hookar publishers

**Inbound (webhook handler):**

```python
# webhook_handler.py
async def handle_webhook(...):
    ...
    for item in parsed:
        if isinstance(item, InboundMessage):
            ...
            append_message(...)
            await bus.publish(f"conversation:{conv.id}", {
                "type": "message.created",
                "data": MessageSchema.from_orm(msg).model_dump(),
            })

        elif isinstance(item, StatusUpdate):
            ...
            await bus.publish(f"conversation:{conv.id}", {
                "type": "message.status_changed",
                "data": {"provider_message_id": ..., "status": ...},
            })

        elif isinstance(item, PresenceUpdate):  # NOVO
            await bus.publish(f"conversation:{conv.id}", {
                "type": "presence.updated",
                "data": {"state": item.state, "expires_at": ...},
            })
```

**Outbound (send message endpoint):**

```python
# após append_message do outbound
await bus.publish(f"conversation:{conv.id}", {
    "type": "message.created",
    "data": ...,
})
```

### Presence inbound

**Evolution event:** `presence.update` (precisa habilitar no painel — já está no spec do user)

Payload Evolution:
```json
{
  "event": "presence.update",
  "data": {
    "id": "5511982956611@s.whatsapp.net",
    "presences": {
      "5511982956611@s.whatsapp.net": {
        "lastKnownPresence": "composing"  // ou "recording", "available", "paused"
      }
    }
  }
}
```

**EvolutionAdapter.parse_webhook** ganha tratamento de `presence.update`:

```python
if event == "presence.update":
    phone = parse_chat_id(data.get("id", ""))
    presences = data.get("presences", {})
    state = (next(iter(presences.values()), {}) or {}).get("lastKnownPresence", "available")
    return [PresenceUpdate(from_phone=phone, state=state, received_at=now())]
```

Novo type:
```python
@dataclass(frozen=True)
class PresenceUpdate:
    from_phone: str
    state: Literal["composing", "recording", "available", "paused", "unavailable"]
    received_at: datetime
```

**Cache pra evitar burst:** presence updates podem chegar em sequência rápida. Cache TTL 8s no `bus.publish` — se já emitiu mesmo estado pra essa conversa nos últimos 2s, skip.

### Presence outbound

**Endpoint novo:** `POST /api/conversations/{id}/typing`

```python
@router.post("/api/conversations/{id}/typing")
async def emit_typing(id: int, ...):
    """Emite composing pro WhatsApp do lead."""
    conv = ...  # lookup
    adapter = get_provider(...)
    adapter.send_presence(to_phone=conv.phone, state="composing")
    return {"ok": True}
```

**EvolutionAdapter.send_presence:**

```python
def send_presence(self, to_phone: str, *, state: str) -> None:
    """POST /chat/sendPresence/{instance}"""
    httpx.post(
        self._url(f"chat/sendPresence/{self.instance}"),
        json={"number": phone, "presence": state, "delay": 2000},
        headers=self._headers(),
        timeout=5.0,
    )
```

Frontend debounce: emite `composing` ao começar a digitar, `paused` após 1.5s sem teclar.

## Frontend

### Hook `useConversationStream`

```ts
// frontend/src/components/inbox/use-conversation-stream.ts
import { useEffect } from "react";
import { mutate } from "swr";

export function useConversationStream(conversationId: number) {
  const [presence, setPresence] = useState<PresenceState | null>(null);

  useEffect(() => {
    const url = `${API_URL}/api/conversations/${conversationId}/stream`;
    const es = new EventSource(url, { withCredentials: true });

    es.addEventListener("message.created", (e) => {
      const msg = JSON.parse(e.data);
      // Invalida SWR cache da conversa pra aparecer na lista
      mutate(`conversation:${conversationId}:messages`);
      mutate("conversations-list");
    });

    es.addEventListener("message.status_changed", (e) => {
      const { provider_message_id, status } = JSON.parse(e.data);
      mutate(`conversation:${conversationId}:messages`, (msgs) =>
        msgs.map(m => m.provider_message_id === provider_message_id ? {...m, status} : m)
      );
    });

    es.addEventListener("presence.updated", (e) => {
      const { state, expires_at } = JSON.parse(e.data);
      setPresence({ state, expires_at: new Date(expires_at) });
    });

    return () => es.close();
  }, [conversationId]);

  // Auto-expire presence client-side
  useEffect(() => {
    if (!presence || presence.state === "available") return;
    const t = setTimeout(() => setPresence(null), 8000);
    return () => clearTimeout(t);
  }, [presence]);

  return { presence };
}
```

### UI presence

Logo abaixo do header da conversa:

```
┌──────────────────────────────┐
│ [AC] Angelo Cerqueira        │
│      responded · (11) ...    │
│ digitando…                   │  ← linha extra, fade in/out
└──────────────────────────────┘
```

- `composing` → "digitando…"
- `recording` → "gravando áudio…"
- `available` / `paused` → esconde linha

### Composer envia typing

```ts
// debounce 500ms entre keystrokes, max 1 emit a cada 3s
const emitTyping = useDebouncedCallback(() => {
  fetch(`/api/conversations/${id}/typing`, { method: "POST" });
}, 500, { maxWait: 3000 });

<textarea onChange={(e) => { setText(e.target.value); emitTyping(); }} />
```

## Edge cases

| Cenário | Comportamento |
|---|---|
| SSE conexão cai (network blip) | EventSource auto-reconecta; servidor pode missar eventos do gap, mas próximo refresh SWR (5s) corrige |
| Múltiplas tabs abertas na mesma conversa | Cada uma abre SSE; bus.publish faz fan-out; todas recebem |
| Slow consumer (queue cheia) | `put_nowait` falha silenciosamente; evento descartado pra aquele subscriber; SWR poll de 5s recupera |
| Lead com `presence.update` rajada (50 eventos/s) | Cache TTL 2s deduplica; max 1 emit a cada 2s por conversation |
| Closer fecha aba durante typing | `paused` não emitido; WhatsApp do lead vai mostrar typing por mais ~3s e expira |
| Multi-worker Railway (futuro) | EventBus in-memory não compartilha entre workers — events emitidos no worker A não chegam ao SSE do worker B. **Mitigação:** docs e ENV check; migrar pra Redis (`aioredis` + pub/sub) quando promover pra multi-worker |
| Conversa não existe (404) | Endpoint retorna 404 antes de subscribe |
| Backpressure | `Queue(maxsize=100)` — se cliente lento, descarta novos eventos pra aquele cliente |

## Decisões tomadas

- **SSE em vez de WebSocket** — unidirecional é suficiente (server → client), HTTP/2 multiplexing, reuso de auth cookie, retry built-in
- **Pub/sub in-memory** — single-worker Railway hoje funciona; abstrair via `EventBus` interface pra trocar por Redis depois sem mexer em call sites
- **Cache presence 2s** — Evolution dispara composing em rajada; sem cache vira spam de UI
- **Debounce typing 500ms + maxWait 3s** — balance entre responsividade e API calls
- **Auto-expire presence client-side em 8s** — se servidor não emite `available`, UI limpa mesmo assim
- **Auth do SSE via cookie** — Bearer não funciona com EventSource sem polyfill; `credentials: "include"` + Better Auth cookie

## Open questions

- **`sendPresence` precisa ser idempotent?** Evolution ignora repeats? **Proposta:** assume idempotent; se causar burst no WhatsApp, adicionar throttle server-side de 1/2s
- **Auto-mark-read** quando user abre conversa? — Não neste spec; depende de UX product decision e endpoint `markAsRead` da Evolution (spec separado de "conversation actions")
- **Heartbeat SSE** pra detectar dead connection? — `EventSourceResponse` do `sse-starlette` envia ping a cada 15s por default. OK.

## Tamanho estimado

M (2-3 dias). Backend: bus + endpoint + presence parsing + send_presence adapter. Frontend: hook + UI + debounce composer. Tests: bus pub/sub, presence parsing, end-to-end SSE flow.

## Referências

- `backend/app/routers/pipeline.py` — padrão SSE existente
- `sse-starlette` docs — `EventSourceResponse`
- Evolution API v2 — `presence.update` event + `POST /chat/sendPresence/{instance}`
- WhatsApp Web — UX de "digitando…" e "gravando áudio…"
