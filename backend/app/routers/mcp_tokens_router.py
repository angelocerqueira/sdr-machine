"""CRUD endpoints pros MCP tokens — usados pela UI /app/settings/mcp."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations.tenant import get_current_workspace_id
from app.mcp.tokens import generate_token, hash_token, list_tokens, revoke_token
from app.models import McpToken

router = APIRouter(prefix="/api/workspace/mcp-tokens", tags=["mcp-tokens"])


class TokenSummary(BaseModel):
    id: int
    name: str
    last4: str
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TokenCreatedOut(TokenSummary):
    token: str


class TokenCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.get("", response_model=list[TokenSummary])
def list_mcp_tokens(request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    rows = list_tokens(db, workspace_id=ws, include_revoked=False)
    return rows


@router.post("", response_model=TokenCreatedOut, status_code=201)
def create_mcp_token(
    payload: TokenCreateIn, request: Request, db: Session = Depends(get_db),
):
    ws = get_current_workspace_id(request)
    plain = generate_token()
    token = McpToken(
        workspace_id=ws, name=payload.name,
        token_hash=hash_token(plain), last4=plain[-4:],
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    return TokenCreatedOut(
        id=token.id, name=token.name, last4=token.last4,
        created_at=token.created_at, last_used_at=token.last_used_at,
        revoked_at=token.revoked_at, token=plain,
    )


@router.delete("/{token_id}", status_code=204)
def revoke_mcp_token(token_id: int, request: Request, db: Session = Depends(get_db)):
    ws = get_current_workspace_id(request)
    row = db.query(McpToken).filter_by(id=token_id, workspace_id=ws).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if row.revoked_at is None:
        revoke_token(db, row.token_hash)
    return None
