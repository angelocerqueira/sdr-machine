# Flows Engine — F-2 Email Channel Adapter Spec

> **Foundation:** [F-0 Architecture](2026-05-17-flows-engine-f0-architecture.md)
> **Status:** ready to plan
> **Depende:** F-0 aprovada (independente de F-1; pode rodar em paralelo)
> **Bloqueia:** F-1 node `send_email` (consome este contrato)

## 1. Objetivo

Criar **contrato `EmailProvider`** (analogia ao `WhatsAppProvider` de P1) + **adapter Resend** + **registry** + **schema email_messages**. Sem rota HTTP — consumido pelo node `send_email` (F-1) e diretamente por qualquer pipeline futuro.

Resend `IntegrationSettings` schema **já existe** (P0/integrations: `ResendConfig` com `api_key`, `from_email`, `from_name`, `reply_to`, `webhook_secret`). Só falta sender + receiver (webhook recv pra status delivered/bounced é opcional MVP).

## 2. Estrutura

```
backend/app/email/
├── __init__.py
├── provider.py           # EmailProvider ABC
├── types.py              # SentEmail, EmailStatus, ProviderHealth (mirrors whatsapp/)
├── resend_adapter.py     # Implementação Resend
├── registry.py           # get_provider(db, workspace_id)
└── normalizer.py         # opcional: validações de email format

backend/tests/test_email_*.py
```

## 3. Contrato `EmailProvider`

```python
# email/provider.py
class EmailProvider(ABC):
    @abstractmethod
    def send(
        self, *, to: str, subject: str, body_html: str,
        body_text: str | None = None, idempotency_key: str | None = None,
    ) -> SentEmail: ...

    @abstractmethod
    def health_check(self) -> ProviderHealth: ...

    @abstractmethod
    def parse_webhook(self, raw: dict) -> list[EmailStatus]:
        """Resend events: email.sent / delivered / opened / clicked / bounced / complained."""
```

Differences vs WhatsApp contract:
- Sem `send_media` (anexos = v2)
- Sem `fetch_history` (Resend não suporta)
- `parse_webhook` retorna só `EmailStatus` (sem inbound — replies são separadas via reply-to email forwarding, fora do MVP)

## 4. Types

```python
# email/types.py
@dataclass(frozen=True)
class SentEmail:
    provider_message_id: str  # Resend `id`
    sent_at: datetime
    status: str  # "queued" | "sent" — Resend retorna "queued" sincronamente

@dataclass(frozen=True)
class EmailStatus:
    provider_message_id: str
    event: Literal["delivered", "opened", "clicked", "bounced", "complained"]
    timestamp: datetime
    metadata: dict | None = None  # bounce reason, etc

@dataclass(frozen=True)
class ProviderHealth:
    ok: bool
    reason: str | None = None
```

## 5. ResendAdapter

```python
# email/resend_adapter.py
class ResendAdapter(EmailProvider):
    BASE_URL = "https://api.resend.com"
    TIMEOUT = 30.0

    def __init__(self, *, api_key: str, from_email: str, from_name: str,
                 reply_to: str | None = None):
        self.api_key = api_key
        self.from_addr = f"{from_name} <{from_email}>"
        self.reply_to = reply_to

    def send(self, *, to, subject, body_html, body_text=None,
             idempotency_key=None) -> SentEmail:
        payload = {
            "from": self.from_addr,
            "to": [to],
            "subject": subject,
            "html": body_html,
        }
        if body_text:
            payload["text"] = body_text
        if self.reply_to:
            payload["reply_to"] = self.reply_to

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key  # Resend suporta nativo

        r = httpx.post(f"{self.BASE_URL}/emails", json=payload,
                       headers=headers, timeout=self.TIMEOUT)
        if r.status_code >= 500:
            raise RetryableError(f"Resend 5xx: {r.text}")
        if r.status_code == 429:
            raise RetryableError(f"Resend rate-limited")
        if r.status_code >= 400:
            raise FatalError(f"Resend {r.status_code}: {r.text}")

        data = r.json()
        return SentEmail(
            provider_message_id=data["id"],
            sent_at=datetime.utcnow(),
            status="queued",
        )

    def health_check(self) -> ProviderHealth:
        try:
            r = httpx.get(f"{self.BASE_URL}/domains",
                          headers={"Authorization": f"Bearer {self.api_key}"},
                          timeout=10.0)
            return ProviderHealth(ok=(r.status_code == 200),
                                  reason=None if r.status_code == 200 else r.text)
        except Exception as e:
            return ProviderHealth(ok=False, reason=str(e))

    def parse_webhook(self, raw: dict) -> list[EmailStatus]:
        """Resend webhook payload format: { type: 'email.delivered', data: {...} }"""
        evt_type = raw.get("type", "")
        if not evt_type.startswith("email."):
            return []
        event = evt_type.removeprefix("email.")
        if event not in {"delivered", "opened", "clicked", "bounced", "complained"}:
            return []
        data = raw.get("data", {})
        msg_id = data.get("email_id") or data.get("id")
        if not msg_id:
            return []
        ts = self._parse_ts(raw.get("created_at") or data.get("created_at"))
        return [EmailStatus(
            provider_message_id=msg_id,
            event=event,  # type: ignore
            timestamp=ts,
            metadata={k: v for k, v in data.items() if k not in {"email_id", "id"}}
        )]
```

## 6. Registry

```python
# email/registry.py
class UnknownEmailProviderError(Exception): ...
class EmailProviderNotConfigured(Exception): ...

_PROVIDERS = {"resend": ResendAdapter}

def get_provider(db: Session, *, workspace_id: int,
                 provider: str = "resend") -> EmailProvider:
    if provider not in _PROVIDERS:
        raise UnknownEmailProviderError(f"Unknown email provider: {provider}")

    config = get_provider_config(db, workspace_id=workspace_id, provider=provider)
    if not config or not config.get("api_key"):
        raise EmailProviderNotConfigured(
            f"Email provider {provider} not configured for workspace {workspace_id}"
        )

    adapter_cls = _PROVIDERS[provider]
    return adapter_cls(
        api_key=config["api_key"],
        from_email=config["from_email"],
        from_name=config["from_name"],
        reply_to=config.get("reply_to"),
    )
```

## 7. Schema `email_messages`

Migration r15 (a próxima livre depois de r14 do F-1):

```python
op.create_table(
    "email_messages",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
    sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
    sa.Column("flow_run_id", sa.Integer, sa.ForeignKey("flow_runs.id", ondelete="SET NULL")),
    sa.Column("provider", sa.String(20), nullable=False, server_default="resend"),
    sa.Column("provider_message_id", sa.String(120), unique=True),
    sa.Column("to_email", sa.String(255), nullable=False),
    sa.Column("subject", sa.Text, nullable=False),
    sa.Column("body_html", sa.Text, nullable=False),
    sa.Column("body_text", sa.Text),
    sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
    sa.Column("sent_at", sa.DateTime),
    sa.Column("delivered_at", sa.DateTime),
    sa.Column("opened_at", sa.DateTime),
    sa.Column("clicked_at", sa.DateTime),
    sa.Column("bounced_at", sa.DateTime),
    sa.Column("complained_at", sa.DateTime),
    sa.Column("failed_reason", sa.Text),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
)
op.create_index("ix_email_messages_lead", "email_messages", ["lead_id"])
op.create_index("ix_email_messages_status", "email_messages", ["status"])
```

## 8. Services

```python
# email/services.py — chamado pelo node send_email do F-1
def record_sent_email(db: Session, *,
    workspace_id, lead_id, flow_run_id, provider, sent: SentEmail,
    to_email, subject, body_html, body_text=None,
) -> EmailMessage:
    """Idempotent: se provider_message_id já existe, retorna existing."""
    existing = db.query(EmailMessage).filter_by(
        provider_message_id=sent.provider_message_id
    ).first()
    if existing:
        return existing
    em = EmailMessage(
        workspace_id=workspace_id, lead_id=lead_id, flow_run_id=flow_run_id,
        provider=provider, provider_message_id=sent.provider_message_id,
        to_email=to_email, subject=subject, body_html=body_html, body_text=body_text,
        status=sent.status, sent_at=sent.sent_at,
    )
    db.add(em)
    db.commit()
    db.refresh(em)
    return em

def update_email_status(db: Session, *,
    provider_message_id: str, status: EmailStatus,
) -> EmailMessage | None:
    """Atualiza timestamps por event. delivered/opened/clicked/bounced/complained."""
    em = db.query(EmailMessage).filter_by(provider_message_id=provider_message_id).first()
    if not em:
        return None
    field_map = {
        "delivered": "delivered_at", "opened": "opened_at",
        "clicked": "clicked_at", "bounced": "bounced_at",
        "complained": "complained_at",
    }
    field = field_map.get(status.event)
    if field:
        setattr(em, field, status.timestamp)
    if status.event in {"bounced", "complained"}:
        em.status = "failed"
        em.failed_reason = status.metadata.get("reason") if status.metadata else status.event
    elif status.event == "delivered":
        em.status = "delivered"
    db.commit()
    return em
```

## 9. Webhook receiver (opcional MVP, recomendado P1)

`POST /api/webhooks/email/{workspace_id}/resend` — análogo ao P2 WhatsApp:
- HMAC verify via `webhook_secret` em IntegrationSettings
- `parse_webhook` → lista EmailStatus
- `update_email_status` por message_id

Pode ser entregue **no mesmo PR de F-2** ou diferido (P1 do MVP funciona sem ele — só perde tracking de delivered/opened/etc).

## 10. Tester

Endpoint `POST /api/workspace/integrations/resend/test` **já existe** (router P0). Confirma funciona com `health_check` do adapter — adicionar test integration que faz mock httpx + chama o endpoint.

## 11. Testing

```
tests/test_email_provider_abc.py     # 1 contrato
tests/test_email_resend_adapter.py   # 12: send 200/400/500/429, idempotency,
                                     #     parse_webhook delivered/bounced/etc, health
tests/test_email_registry.py         # 5: resolve, not_configured, unknown, etc
tests/test_email_services.py         # 6: record idempotent, update_status events
```

## 12. Critérios de aceite

- [ ] Migration r15 aplica/reverte
- [ ] `ResendAdapter.send()` faz POST autenticado + retorna `SentEmail` parseado
- [ ] Erros 5xx/429 → `RetryableError`; 4xx → `FatalError`
- [ ] `parse_webhook` cobre 5 event types Resend (delivered/opened/clicked/bounced/complained)
- [ ] `record_sent_email` é idempotent por `provider_message_id`
- [ ] `update_email_status` mapeia event → coluna timestamp + status="delivered/failed"
- [ ] Health check passa com httpx_mock cobrindo 200 e timeout
- [ ] 25+ testes novos sem regressão

## 13. Não coberto

- Anexos (multipart)
- Inbound reply parsing (Resend não tem; cliente teria que setar forward MX)
- Template engine em provider (templates ficam no node `send_email` do F-1)
- Tracking pixel custom
- A/B variants
- Email webhook receiver — se diferido, vira F-2.5
