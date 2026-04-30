"""Endpoints de configuração de workspace.

Hoje single-workspace (workspace_id=1). Quando virar multi-tenant
o helper get_current_workspace_id resolve do session — call sites não mudam.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

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
    business_name: str | None
    your_name: str | None
    your_email: str | None
    your_whatsapp: str | None
    your_website: str | None
    legal_basis: str | None

    class Config:
        from_attributes = True


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
    class Config:
        from_attributes = True


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
