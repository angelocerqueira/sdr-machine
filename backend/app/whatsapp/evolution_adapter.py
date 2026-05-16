"""Evolution API adapter — implementa WhatsAppProvider.

Evolution roda em cima do protocolo WhatsApp Web (Baileys). Endpoints
REST com header `apikey`. Stateless por chamada; sessão WhatsApp mora
do lado do servidor Evolution (instância).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.whatsapp.normalizer import (
    normalize_phone_br,
    parse_chat_id,
    to_chat_id,
)
from app.whatsapp.provider import WhatsAppProvider
from app.whatsapp.types import (
    InboundMessage,
    ProviderHealth,
    SentMessage,
    StatusUpdate,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0


class EvolutionAdapter(WhatsAppProvider):
    name = "evolution"

    def __init__(self, *, base_url: str, instance: str, api_key: str,
                 timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.instance = instance
        self.api_key = api_key
        self.timeout = timeout

    # --- privates ---
    def _headers(self, idempotency_key: str | None = None) -> dict:
        h = {"apikey": self.api_key, "Content-Type": "application/json"}
        if idempotency_key:
            h["X-Idempotency-Key"] = idempotency_key
        return h

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    # --- send_text ---
    def send_text(self, to_phone: str, body: str, *, idempotency_key: str) -> SentMessage:
        phone = normalize_phone_br(to_phone)
        r = httpx.post(
            self._url(f"message/sendText/{self.instance}"),
            json={"number": phone, "text": body},
            headers=self._headers(idempotency_key),
            timeout=self.timeout,
        )
        if r.status_code not in (200, 201):
            logger.warning("Evolution send_text failed: %s %s", r.status_code, r.text[:200])
            raise RuntimeError(
                f"Evolution send_text failed: status={r.status_code} body={r.text[:200]}"
            )
        payload = r.json()
        msg_id = (payload.get("key") or {}).get("id") or ""
        return SentMessage(
            provider_message_id=msg_id,
            sent_at=datetime.now(timezone.utc),
            phone_to=phone,
            body=body,
            status="sent",
        )

    _MEDIA_EXT_MAP = {
        "image": {"jpg", "jpeg", "png", "gif", "webp"},
        "video": {"mp4", "mov", "webm"},
        "audio": {"mp3", "ogg", "wav", "m4a"},
        "document": {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"},
    }

    def _infer_mediatype(self, media_url: str) -> str:
        ext = media_url.rsplit(".", 1)[-1].lower().split("?")[0]
        for kind, exts in self._MEDIA_EXT_MAP.items():
            if ext in exts:
                return kind
        return "document"

    def send_media(self, to_phone: str, media_url: str,
                   caption: str | None = None) -> SentMessage:
        phone = normalize_phone_br(to_phone)
        mediatype = self._infer_mediatype(media_url)
        body = {
            "number": phone,
            "mediatype": mediatype,
            "media": media_url,
        }
        if caption:
            body["caption"] = caption
        r = httpx.post(
            self._url(f"message/sendMedia/{self.instance}"),
            json=body,
            headers=self._headers(),
            timeout=self.timeout,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"Evolution send_media failed: status={r.status_code} body={r.text[:200]}"
            )
        payload = r.json()
        msg_id = (payload.get("key") or {}).get("id") or ""
        return SentMessage(
            provider_message_id=msg_id,
            sent_at=datetime.now(timezone.utc),
            phone_to=phone,
            body=caption or "",
            status="sent",
        )

    # --- placeholders pra próximas tasks ---

    def fetch_history(self, phone, *, limit=50):
        raise NotImplementedError("Task 8")

    def parse_webhook(self, raw):
        raise NotImplementedError("Task 9")

    def health_check(self):
        raise NotImplementedError("Task 10")
