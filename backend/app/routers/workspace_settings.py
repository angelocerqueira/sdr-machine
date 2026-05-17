"""Endpoints de configuração de workspace.

Hoje single-workspace (workspace_id=1). Quando virar multi-tenant
o helper get_current_workspace_id resolve do session — call sites não mudam.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.integrations.tenant import get_current_workspace_id
from app.models import WorkspaceProfile, WorkspaceTargeting

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# ─────── Profile ───────

class ProfileIn(BaseModel):
    business_name: str | None = None
    your_name: str | None = None
    your_email: EmailStr | None = None
    your_whatsapp: str | None = None
    your_website: str | None = None
    legal_basis: str | None = None


class ProfileOut(BaseModel):
    model_config = {"from_attributes": True}

    business_name: str | None
    your_name: str | None
    your_email: str | None
    your_whatsapp: str | None
    your_website: str | None
    legal_basis: str | None


def _get_or_create_profile(db: Session, ws: int) -> WorkspaceProfile:
    row = db.query(WorkspaceProfile).filter_by(workspace_id=ws).first()
    if row is None:
        row = WorkspaceProfile(workspace_id=ws, legal_basis="legitimo_interesse_b2b")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/profile", response_model=ProfileOut)
def get_profile(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    return _get_or_create_profile(db, ws)


@router.put("/profile", response_model=ProfileOut)
def put_profile(payload: ProfileIn, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = _get_or_create_profile(db, ws)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ─────── Targeting ───────

class TargetingIn(BaseModel):
    target_niches: list[str] | None = None
    target_cities: list[str] | None = None
    min_rating: float | None = None
    max_results_per_search: int | None = None
    opportunity_score_threshold: int | None = None
    diagnostic_model: str | None = None
    skip_ai_diagnostic: bool | None = None
    skip_social_scraping: bool | None = None
    ai_potential_threshold: int | None = None
    disqualify_threshold: int | None = None
    skip_service_level_analysis: bool | None = None


class TargetingOut(TargetingIn):
    model_config = {"from_attributes": True}


def _get_or_create_targeting(db: Session, ws: int) -> WorkspaceTargeting:
    row = db.query(WorkspaceTargeting).filter_by(workspace_id=ws).first()
    if row is None:
        row = WorkspaceTargeting(workspace_id=ws, target_niches=[], target_cities=[])
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/targeting", response_model=TargetingOut)
def get_targeting(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    return _get_or_create_targeting(db, ws)


@router.put("/targeting", response_model=TargetingOut)
def put_targeting(payload: TargetingIn, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = _get_or_create_targeting(db, ws)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ─────── Integrations ───────
import datetime as _dt

from cryptography.fernet import InvalidToken

from app.integrations.crypto import decrypt, encrypt
from app.integrations.resolver import _decrypt_secrets  # shared logic within app.integrations
from app.integrations.schemas import PROVIDER_SCHEMAS, SECRET_FIELDS
from app.integrations.testers import run_test
from app.models import IntegrationSettings

KNOWN_PROVIDERS = list(PROVIDER_SCHEMAS.keys())


def _mask_config(provider: str, raw: dict) -> dict:
    """Aplica mask em campos secretos e expõe flags has_*/last4 pra UI.

    Decifra cada secret individualmente. Se o ciphertext estiver corrompido
    (key rotation sem re-encrypt, restore parcial, edição manual de DB), marca
    `needs_reencrypt=true` e segue — sem isso, uma linha ruim quebraria
    GET /integrations inteiro com 500.
    """
    secrets = SECRET_FIELDS.get(provider, set())
    out = {}
    for k, v in raw.items():
        if k in secrets:
            continue  # secret nunca volta em plain
        out[k] = v

    needs_reencrypt = False
    for field in secrets:
        cipher = raw.get(field)
        if not cipher or not isinstance(cipher, str):
            out[f"has_{field}"] = False
            continue
        out[f"has_{field}"] = True
        try:
            val = decrypt(cipher)
        except InvalidToken:
            needs_reencrypt = True
            continue
        if val:
            out[f"{field}_last4"] = val[-4:] if len(val) >= 4 else val

    if needs_reencrypt:
        out["needs_reencrypt"] = True
    return out


def _serialize(row: IntegrationSettings) -> dict:
    return {
        "provider": row.provider,
        "enabled": row.enabled,
        "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
        "last_test_result": row.last_test_result,
        "config": _mask_config(row.provider, row.config or {}),
    }


def _stub(provider: str) -> dict:
    return {
        "provider": provider,
        "enabled": False,
        "last_tested_at": None,
        "last_test_result": None,
        "config": _mask_config(provider, {}),
    }


@router.get("/integrations")
def list_integrations(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    rows = {r.provider: r for r in db.query(IntegrationSettings).filter_by(workspace_id=ws).all()}
    return [_serialize(rows[p]) if p in rows else _stub(p) for p in KNOWN_PROVIDERS]


@router.get("/integrations/{provider}")
def get_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()
    return _serialize(row) if row else _stub(provider)


class IntegrationPut(BaseModel):
    config: dict
    enabled: bool | None = None


@router.put("/integrations/{provider}")
def put_integration(provider: str, payload: IntegrationPut, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()

    new_config = dict(row.config) if row else {}
    secrets = SECRET_FIELDS[provider]

    for k, v in payload.config.items():
        if k in secrets:
            # vazio = ignorado (mantém atual)
            if v is None or v == "":
                continue
            new_config[k] = encrypt(v)
        else:
            new_config[k] = v

    # Validar shape com Pydantic — testes só fazem sentido se schema completo
    schema = PROVIDER_SCHEMAS[provider]
    try:
        decrypted = _decrypt_secrets(provider, new_config)
    except InvalidToken:
        raise HTTPException(
            422,
            f"Stored secret for {provider} is corrupted (Fernet key rotated or row tampered). "
            f"Re-paste the credential to overwrite.",
        )
    try:
        schema.model_validate(decrypted)
    except Exception as exc:
        raise HTTPException(400, f"Invalid config for {provider}: {exc}")

    if row is None:
        row = IntegrationSettings(
            workspace_id=ws, provider=provider,
            config=new_config, enabled=True,
        )
        db.add(row)
    else:
        row.config = new_config
        if payload.enabled is not None:
            row.enabled = payload.enabled

    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/integrations/{provider}", status_code=204)
def delete_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).delete()
    db.commit()
    return None


_WEBHOOK_URL_PROVIDERS = {"evolution"}


@router.get("/integrations/{provider}/webhook-url")
def get_webhook_url(provider: str, request: Request):
    """URL pública do webhook pra este workspace/provider.

    Frontend exibe num input read-only com botão copy em
    `/app/settings/integracoes`. Provider precisa estar no allowlist
    (atualmente: evolution).
    """
    if provider not in _WEBHOOK_URL_PROVIDERS:
        raise HTTPException(status_code=404, detail="provider not found")
    ws = get_current_workspace_id(request)
    base = (app_settings.api_url or "http://localhost:8000").rstrip("/")
    return {"url": f"{base}/api/webhooks/whatsapp/{ws}/{provider}"}


@router.post("/integrations/{provider}/test")
def test_integration(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in PROVIDER_SCHEMAS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    ws = get_current_workspace_id(request)
    row = db.query(IntegrationSettings).filter_by(workspace_id=ws, provider=provider).first()
    if row is None or not row.config:
        raise HTTPException(400, "Integration not configured")

    try:
        cfg = _decrypt_secrets(provider, row.config)
    except InvalidToken:
        raise HTTPException(
            422,
            f"Stored secret for {provider} is corrupted (Fernet key rotated or row tampered). "
            f"Re-save the credential before testing.",
        )
    res = run_test(provider, cfg)
    row.last_tested_at = _dt.datetime.utcnow()
    row.last_test_result = res.to_dict()
    db.commit()
    return res.to_dict()
