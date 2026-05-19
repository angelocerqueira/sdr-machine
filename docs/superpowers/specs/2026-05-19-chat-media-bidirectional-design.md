# Chat — Mídia bidirecional (inbound + outbound) — Design

**Status:** specced — pending plan

**Goal:** Closer recebe e envia mídia pelo Inbox: imagens, áudios de voz, documentos PDF. Sem mídia, conversa profissional não rola — concorrentes desclassificam o produto na primeira foto enviada.

**Arquitetura:** Storage externo pra binários (Cloudflare R2 ou S3). Backend baixa mídia inbound do Evolution → grava em storage → URL pública assinada → DB. Para outbound, recebe upload do frontend → grava em storage → URL → Evolution. Composer expandido com botão de anexo e gravador de áudio.

**Tech:** Cloudflare R2 (S3-compatible, mais barato), `boto3` no backend, MediaRecorder API + WebAudio no frontend.

---

## Problema

Hoje:
- Lead manda foto pelo WhatsApp → webhook chega com `messageType: imageMessage`
- `EvolutionAdapter._extract_body()` lê apenas `message.conversation` (texto puro) → retorna `None`
- Handler grava `ConversationMessage(body=None)` — UI mostra bolha vazia
- Outbound: composer só tem texto. Closer não consegue mandar PDF de proposta ou áudio explicativo

## Escopo

### In scope (MVP)

**Recebimento:**
- Imagens (`imageMessage`)
- Áudios de voz (`audioMessage` com `ptt: true`)
- Documentos (`documentMessage` — PDF, DOCX, XLSX)
- Vídeos curtos (`videoMessage`)

**Envio:**
- Anexar imagem (drag-drop ou botão 📎)
- Anexar documento (PDF até 16MB — limite Evolution)
- Gravar áudio voice note (botão 🎤 hold-to-record, igual WhatsApp)

### Out of scope

- Sticker (volta em PR menor)
- Localização, contato vCard, poll, lista interativa
- Compressão de mídia client-side (cliente Evolution já comprime)
- Stream de vídeo longo
- Multi-attach (1 envio por vez no MVP)

## Modelo de dados

Adicionar campos em `ConversationMessage`:

```python
class ConversationMessage(Base):
    ...
    media_type: Column(String(20), nullable=True)
    # 'image' | 'audio' | 'document' | 'video' | 'sticker' | null pra texto

    media_url: Column(String(512), nullable=True)
    # URL pública assinada do nosso storage (R2/S3)

    media_filename: Column(String(255), nullable=True)
    # nome original do arquivo (pra documentos: "proposta.pdf")

    media_mimetype: Column(String(100), nullable=True)
    # ex: "image/jpeg", "audio/ogg; codecs=opus", "application/pdf"

    media_size_bytes: Column(Integer, nullable=True)

    media_duration_sec: Column(Integer, nullable=True)
    # só pra audio/video

    media_caption: Column(Text, nullable=True)
    # texto que acompanha mídia (imagem com legenda)
```

Migration nova: `alembic/versions/<timestamp>_add_media_to_conversation_message.py`

## Backend

### Storage abstraction (`backend/app/storage/`)

Nova camada — abstrai backend de storage pra permitir trocar entre R2/S3/local:

```python
# backend/app/storage/base.py
class MediaStorage(ABC):
    def upload(self, key: str, content: bytes, mimetype: str) -> str:
        """Returns public URL"""
    def get_signed_url(self, key: str, ttl_sec: int = 3600) -> str: ...
    def delete(self, key: str) -> None: ...

# backend/app/storage/r2.py — implementação R2
class R2Storage(MediaStorage): ...

# backend/app/storage/local.py — dev/test fallback
class LocalStorage(MediaStorage): ...
```

Config via env:
- `MEDIA_STORAGE_BACKEND` = `r2` | `s3` | `local` (default: local em dev)
- `MEDIA_STORAGE_BUCKET`
- `MEDIA_STORAGE_PUBLIC_URL_BASE`
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT_URL`

Tamanho máx via `MEDIA_MAX_SIZE_MB` (default 16).

### Inbound pipeline (mídia chegando)

**EvolutionAdapter.parse_webhook** — expandir pra detectar tipo:

```python
def parse_webhook(self, raw) -> list[...]:
    ...
    if event == "messages.upsert":
        msg = data.get("message") or {}
        media_info = self._extract_media(msg)
        # InboundMessage agora carrega media_info opcional
        return [InboundMessage(
            ...,
            push_name=...,
            media=media_info,  # None ou MediaPayload
        )]

def _extract_media(self, message: dict) -> MediaPayload | None:
    """Detecta image/audio/video/document e extrai url, mimetype, size."""
    if "imageMessage" in message:
        m = message["imageMessage"]
        return MediaPayload(
            type="image",
            evolution_url=m.get("url"),
            mimetype=m.get("mimetype", "image/jpeg"),
            size_bytes=m.get("fileLength"),
            caption=m.get("caption"),
        )
    if "audioMessage" in message:
        m = message["audioMessage"]
        return MediaPayload(
            type="audio",
            evolution_url=m.get("url"),
            mimetype=m.get("mimetype", "audio/ogg; codecs=opus"),
            duration_sec=m.get("seconds"),
            size_bytes=m.get("fileLength"),
        )
    # documentMessage, videoMessage equivalente
    return None
```

**Webhook handler** — quando `inbound.media` existe, dispara background download:

```python
if item.media:
    # Download asíncrono pra não bloquear webhook response
    background_tasks.add_task(
        download_and_persist_media,
        message_id=appended_message.id,
        evolution_url=item.media.evolution_url,
        ...
    )
```

`download_and_persist_media`:
1. Baixa via `httpx.get(evolution_url)` com timeout 30s
2. Sobe pro storage com key `media/{workspace_id}/{message_id}/{filename}`
3. Atualiza `ConversationMessage.media_url` com URL pública

### Outbound pipeline (mídia sendo enviada)

**Endpoint novo** — `POST /api/conversations/{id}/messages/media`:

```python
@router.post("/api/conversations/{id}/messages/media")
async def send_media_message(
    id: int, file: UploadFile, caption: str = Form(""), kind: str = Form("image"),
    db: Session = Depends(get_db),
):
    # 1. Validar tamanho + tipo
    # 2. Upload pro storage → URL pública
    # 3. Adapter.send_media(phone, url, kind, caption)
    # 4. Append ConversationMessage(direction="out", media_*=...)
    # 5. Return MessageOut
```

Validação:
- Tamanho ≤ `MEDIA_MAX_SIZE_MB`
- Mimetype permitido por `kind`:
  - `image` → `image/jpeg`, `image/png`, `image/webp`
  - `audio` → `audio/ogg`, `audio/mpeg`, `audio/mp4`
  - `document` → `application/pdf`, `application/msword`, sheets, etc
  - `video` → `video/mp4`, `video/webm`

**EvolutionAdapter** ganha métodos:

```python
def send_media(self, to_phone: str, *, media_url: str, kind: str, caption: str = "",
               filename: str = "", idempotency_key: str) -> SentMessage:
    """POST /message/sendMedia/{instance}"""
    payload = {
        "number": phone,
        "mediatype": kind,  # "image" | "document" | "video"
        "media": media_url,
        "caption": caption,
        "fileName": filename,
    }
    ...

def send_voice(self, to_phone: str, *, audio_url: str, idempotency_key: str) -> SentMessage:
    """POST /message/sendWhatsAppAudio/{instance} — voice note com waveform"""
    payload = {"number": phone, "audio": audio_url, "encoding": True}
    ...
```

## Frontend

### Composer expandido

```
┌────────────────────────────────────────────────────────┐
│ [📎] [🎤] [Mensagem...                       ]  [Enviar] │
└────────────────────────────────────────────────────────┘
```

- `📎` (paperclip): abre file picker; aceita `image/*,application/pdf,video/mp4`
- `🎤` (mic): hold-to-record com MediaRecorder API → preview com play/cancel/send

Componentes novos (`frontend/src/components/inbox/`):
- `ComposerAttachButton.tsx` — file picker + preview chip antes de enviar
- `ComposerVoiceRecorder.tsx` — botão hold, timer, waveform live, send/cancel
- `MediaPreviewModal.tsx` — modal antes do envio (preview imagem, info doc, áudio play)

### MessageBubble por tipo

```tsx
function MessageBubble({ msg }) {
  if (msg.media_type === "image") return <ImageBubble src={msg.media_url} caption={msg.body} />;
  if (msg.media_type === "audio") return <AudioBubble src={msg.media_url} duration={msg.media_duration_sec} />;
  if (msg.media_type === "document") return <DocumentBubble url={msg.media_url} filename={msg.media_filename} />;
  if (msg.media_type === "video") return <VideoBubble src={msg.media_url} />;
  return <TextBubble text={msg.body} />;
}
```

- **ImageBubble**: thumbnail clicável → lightbox; legenda abaixo
- **AudioBubble**: play/pause + barra de progresso + duração; waveform simples (não bloqueia MVP)
- **DocumentBubble**: ícone tipo arquivo + filename + tamanho + botão "Abrir"
- **VideoBubble**: thumb com play overlay → lightbox com `<video>` nativo

### Upload flow

1. User clica 📎 → seleciona arquivo
2. Frontend valida tamanho/tipo client-side
3. Mostra preview chip no composer com nome + tamanho + "x" pra cancelar
4. User adiciona caption opcional + Enviar
5. POST multipart pro backend
6. Backend retorna `MessageOut` com `media_url` já populado
7. Composer limpa, mensagem aparece otimisticamente

### Voice recording flow

1. User clica e segura 🎤 (`mousedown` / `touchstart`)
2. Solicita permissão de microfone (1ª vez)
3. Inicia gravação via `MediaRecorder({mimeType: "audio/webm"})`
4. Mostra timer + indicador visual (bolinha pulsante vermelha)
5. User solta:
   - Slide-up para cancelar
   - Solta no botão: preview do áudio com play
6. User confirma Enviar → upload → send_voice

**Detalhes técnicos:**
- Codec preferido: `audio/webm; codecs=opus` (Chrome/Firefox), fallback `audio/mp4`
- Backend converte pra Opus em OGG se vier outro formato (Evolution exige OGG/Opus)
- Conversão via `ffmpeg-python` ou pyav

## Edge cases

| Cenário | Comportamento |
|---|---|
| Mídia inbound > tamanho máx | Download skip + flag `media_too_large`; UI mostra "Arquivo muito grande (X MB)" |
| Evolution URL expirou antes do download | Retry 1x com delay; se ainda falha, marca `media_download_failed` + mostra fallback |
| Upload outbound durante envio: usuário fecha aba | Upload aborta; nada persistido; UI volta ao estado anterior |
| Mídia já no storage (idempotency) | Hash MD5 do conteúdo como parte da key — dedupe |
| Mimetype não confiável (cliente mente) | Magic bytes check no backend (python-magic) antes de aceitar |
| Browser sem MediaRecorder support | Esconde botão 🎤 + tooltip "Atualize o navegador" |
| Latência alta no upload | Progress bar no chip; cancel disponível |
| Lead manda áudio em formato esquisito | Frontend usa `<audio src>` direto da `media_url` — browser lida; se falha, mostra "Mídia indisponível" |

## Segurança

- URLs públicas no R2: usar `signed_url` com TTL 7 dias pra mídia inbound (não queremos mídia exposta indefinidamente)
- Path traversal: keys construídas server-side só com `workspace_id` + `message_id` + slug filename
- Magic bytes check pra rejeitar uploads malicious (ex: arquivo `.exe` renomeado pra `.pdf`)
- Não baixar mídia de URL externa fora do domínio Evolution conhecido (whitelist)

## Decisões tomadas

- **Cloudflare R2** em vez de AWS S3 — sem egress fees, custo previsível pra produto early
- **Background download** da mídia inbound — webhook responde 200 imediato, mídia aparece em ~5s
- **Voice notes em Opus/OGG** — formato nativo do WhatsApp; converter no backend evita complexidade no frontend
- **Sem compressão client-side no MVP** — confiar no Evolution (que comprime no envio) e nos arquivos do usuário
- **TTL 7 dias** nas signed URLs — balance entre privacidade e usabilidade (lead acessa histórico)
- **Tamanho máx 16 MB** — limite hard do Evolution/WhatsApp

## Open questions

- **Conversão Opus** no backend bloqueia o pipeline? Usar `ffmpeg` no container Railway? Ou worker separado? **Proposta:** ffmpeg no Dockerfile + conversão sync no endpoint (200ms-2s aceitável)
- **Vídeo > 5 segundos** precisa de thumbnail gerado? **Proposta:** sim, gerar com ffmpeg + storage separado; preguiçoso na 1ª view se preferir
- **Renderização de waveform** — calcular no backend ao receber áudio, salvar peaks em JSON? Ou render no frontend a partir do blob? **Proposta:** frontend lazy via Web Audio API; sem peaks no DB

## Tamanho estimado

M-L (3-4 dias). Backend storage + adapter + endpoint + migration + frontend composer + bubbles + voice recorder. Tests covering inbound parse, outbound flow, upload validation, voice encoding.

## Referências

- Evolution API v2 — `POST /message/sendMedia/{instance}`, `POST /message/sendWhatsAppAudio/{instance}`
- WhatsApp Web — voice note UX (hold to record)
- Cloudflare R2 — `boto3` config com `endpoint_url`
- Chatwoot — message rendering por tipo
