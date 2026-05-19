"""POST /api/webhooks/whatsapp/{workspace_id}/{provider}

Endpoint público. Autenticação varia por provider:
- Evolution v2: apikey no body (provider não tem HMAC nativo)
- Demais providers: HMAC via header X-Sdr-Signature
"""
from __future__ import annotations

import hmac as _hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.resolver import get_provider_config
from app.whatsapp.hmac import verify_signature
from app.whatsapp.webhook_handler import (
    WebhookHandlerError,
    handle_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

SIGNATURE_HEADER = "X-Sdr-Signature"


@router.post("/whatsapp/{workspace_id}/{provider}")
async def whatsapp_webhook(
    workspace_id: int, provider: str, request: Request,
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    cfg = get_provider_config(db, workspace_id=workspace_id, provider=provider)
    if cfg is None:
        logger.warning(
            "webhook.unauthorized workspace=%s provider=%s reason=no_config",
            workspace_id, provider,
        )
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    if provider == "evolution":
        # Evolution v2 não assina via HMAC. Manda apikey-da-instance no body
        # (diferente da apikey global). Cacheamos `instance_token` no save/test
        # via /api/workspace/integrations/evolution. Fallback pra api_key
        # (global) só pra não quebrar configs antigas que ainda não rodaram
        # /test — o caminho recomendado é cachear instance_token.
        received_key = str((payload or {}).get("apikey") or "")
        expected = cfg.get("instance_token") or cfg.get("api_key") or ""
        if not expected or not received_key or not _hmac.compare_digest(
            str(expected), received_key,
        ):
            logger.warning(
                "webhook.invalid_apikey workspace=%s provider=%s has_instance_token=%s",
                workspace_id, provider, bool(cfg.get("instance_token")),
            )
            raise HTTPException(status_code=401, detail="invalid apikey")
    else:
        if not cfg.get("webhook_secret"):
            logger.warning(
                "webhook.unauthorized workspace=%s provider=%s reason=no_secret",
                workspace_id, provider,
            )
            raise HTTPException(status_code=401, detail="invalid signature")
        signature = request.headers.get(SIGNATURE_HEADER)
        if not verify_signature(cfg["webhook_secret"], raw_body, signature):
            logger.warning(
                "webhook.invalid_signature workspace=%s provider=%s",
                workspace_id, provider,
            )
            raise HTTPException(status_code=401, detail="invalid signature")

    try:
        summary = handle_webhook(
            db, workspace_id=workspace_id, provider=provider, raw=payload,
        )
    except WebhookHandlerError as exc:
        logger.warning(
            "webhook.handler_error workspace=%s provider=%s error=%s",
            workspace_id, provider, exc,
        )
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(
        "webhook.processed workspace=%s provider=%s summary=%s",
        workspace_id, provider, summary,
    )
    return {"ok": True, "summary": summary}
