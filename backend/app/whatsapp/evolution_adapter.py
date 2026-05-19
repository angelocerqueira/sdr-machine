"""Evolution API adapter — implementa WhatsAppProvider.

Evolution roda em cima do protocolo WhatsApp Web (Baileys). Endpoints
REST com header `apikey`. Stateless por chamada; sessão WhatsApp mora
do lado do servidor Evolution (instância).
"""
from __future__ import annotations

import logging
import time
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

    # --- fetch_history ---
    @staticmethod
    def _extract_body(msg_payload: dict) -> str | None:
        """Evolution serializa texto em formatos diferentes."""
        if not msg_payload:
            return None
        if "conversation" in msg_payload:
            return msg_payload["conversation"]
        ext = msg_payload.get("extendedTextMessage") or {}
        if "text" in ext:
            return ext["text"]
        return None

    def fetch_history(self, phone: str, *, limit: int = 50) -> list[InboundMessage]:
        phone_norm = normalize_phone_br(phone)
        chat_id = to_chat_id(phone_norm)
        r = httpx.get(
            self._url(f"chat/findMessages/{self.instance}"),
            params={"where[key][remoteJid]": chat_id, "limit": limit},
            headers=self._headers(),
            timeout=self.timeout,
        )
        if r.status_code != 200:
            raise RuntimeError(
                f"Evolution fetch_history failed: status={r.status_code} body={r.text[:200]}"
            )
        raw_msgs = r.json() or []
        result: list[InboundMessage] = []
        for raw in raw_msgs:
            key = raw.get("key") or {}
            if key.get("fromMe", False):
                continue  # outbound — fora do escopo (vem do nosso DB)
            body = self._extract_body(raw.get("message") or {})
            ts = raw.get("messageTimestamp")
            received_at = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc)
                if ts is not None else datetime.now(timezone.utc)
            )
            try:
                from_phone = parse_chat_id(key.get("remoteJid", ""))
            except ValueError:
                continue  # grupos — skip
            result.append(InboundMessage(
                provider_message_id=key.get("id", ""),
                from_phone=from_phone,
                body=body,
                received_at=received_at,
            ))
        return result

    # --- parse_webhook ---
    _STATUS_MAP = {
        "PENDING": "queued",
        "SERVER_ACK": "sent",
        "DELIVERY_ACK": "delivered",
        "READ": "read",
        "PLAYED": "read",
        "ERROR": "failed",
    }

    def parse_webhook(self, raw: dict) -> list[InboundMessage | StatusUpdate]:
        event = raw.get("event") or ""
        data = raw.get("data") or {}

        if event == "messages.upsert":
            key = data.get("key") or {}
            if key.get("fromMe", False):
                return []
            try:
                from_phone = parse_chat_id(key.get("remoteJid", ""))
            except ValueError:
                return []  # grupos
            body = self._extract_body(data.get("message") or {})
            ts = data.get("messageTimestamp")
            received_at = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc)
                if ts is not None else datetime.now(timezone.utc)
            )
            return [InboundMessage(
                provider_message_id=key.get("id", ""),
                from_phone=from_phone,
                body=body,
                received_at=received_at,
                push_name=data.get("pushName") or None,
            )]

        if event == "messages.update":
            key = data.get("key") or {}
            update = data.get("update") or {}
            evo_status = (update.get("status") or "").upper()
            mapped = self._STATUS_MAP.get(evo_status)
            if not mapped:
                return []
            return [StatusUpdate(
                provider_message_id=key.get("id", ""),
                status=mapped,  # type: ignore[arg-type]
                timestamp=datetime.now(timezone.utc),
            )]

        return []

    # --- connect_instance ---
    def connect_instance(self) -> dict:
        """Inicia connection flow da instance — retorna QR code base64 + estado atual.

        Evolution: GET /instance/connect/<instance>
        Response shape (varia entre versões): { base64, code, pairingCode?, state? }
        """
        t0 = time.monotonic()
        try:
            r = httpx.get(
                self._url(f"instance/connect/{self.instance}"),
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "evolution.connect.unreachable instance=%s exc=%s",
                self.instance, exc,
            )
            return {
                "ok": False,
                "error": "Evolution server unreachable",
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        if r.status_code != 200:
            logger.warning(
                "evolution.connect.http_error instance=%s status=%s body=%r",
                self.instance, r.status_code, r.text[:500],
            )
            return {
                "ok": False,
                "error": f"Evolution returned {r.status_code}",
                "status_code": r.status_code,
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        body = r.json() if r.text else {}
        # Normalize fields — Evolution version variability:
        qr_base64 = (
            body.get("base64")
            or (body.get("qrcode") or {}).get("base64")
            or None
        )
        pairing_code = body.get("pairingCode") or body.get("pairing_code")
        code = body.get("code") or (body.get("qrcode") or {}).get("code")
        return {
            "ok": True,
            "qr_base64": qr_base64,
            "pairing_code": pairing_code,
            "code": code,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }

    # --- logout_instance ---
    def logout_instance(self) -> dict:
        """Desconecta a sessão WhatsApp sem deletar a instance.

        Evolution: DELETE /instance/logout/<instance>. State vai pra `close`.
        Instance, credenciais e webhook config preservados. Próximo
        connect_instance() gera QR novo.
        """
        t0 = time.monotonic()
        try:
            r = httpx.delete(
                self._url(f"instance/logout/{self.instance}"),
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            return {
                "ok": False,
                "error": f"unreachable: {str(exc)[:200]}",
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        latency_ms = int((time.monotonic() - t0) * 1000)
        # Evolution v2 retorna 200 com {"status":"SUCCESS"} ou 404 se já desconectado
        if r.status_code == 404:
            return {"ok": True, "already_disconnected": True, "latency_ms": latency_ms}
        if r.status_code >= 400:
            return {"ok": False, "error": r.text[:200], "latency_ms": latency_ms}
        return {"ok": True, "latency_ms": latency_ms}

    # --- fetch_instance_token ---
    def fetch_instance_token(self) -> str | None:
        """Resolve a apikey específica da instance via /instance/fetchInstances.

        Evolution v2 envia essa key (e não a global) no body do webhook —
        precisamos cachear pra comparar no receiver. Retorna None se a
        instance não existir ou se a chamada falhar.
        """
        try:
            r = httpx.get(
                self._url("instance/fetchInstances"),
                params={"instanceName": self.instance},
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("evolution.fetch_instances failed: %s", exc)
            return None
        if r.status_code != 200:
            logger.warning(
                "evolution.fetch_instances status=%s body=%s",
                r.status_code, r.text[:200],
            )
            return None
        items = r.json() if r.text else []
        if not isinstance(items, list):
            return None
        for item in items:
            # Evolution v2 retorna em formatos variados entre versões:
            # - {"name": "sdr", "token": "..."} (flat, v2.x recentes)
            # - {"instance": {"instanceName": "sdr"}, "hash": {"apikey": "..."}} (legado)
            name = item.get("name") or (item.get("instance") or {}).get("instanceName")
            if name != self.instance:
                continue
            token = item.get("token")
            if not token:
                token = (item.get("hash") or {}).get("apikey")
            if token:
                return str(token)
        return None

    # --- health_check ---
    def health_check(self) -> ProviderHealth:
        t0 = time.monotonic()
        try:
            r = httpx.get(
                self._url(f"instance/connectionState/{self.instance}"),
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            return ProviderHealth(
                ok=False, state="unreachable",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error=str(exc)[:200],
            )
        latency_ms = int((time.monotonic() - t0) * 1000)
        if r.status_code != 200:
            return ProviderHealth(
                ok=False, state="error", latency_ms=latency_ms, error=r.text[:200],
            )
        body = r.json() if r.text else {}
        state = (body.get("instance") or {}).get("state", "unknown")
        return ProviderHealth(
            ok=state == "open", state=state, latency_ms=latency_ms,
            error=None if state == "open" else f"state={state}",
        )
