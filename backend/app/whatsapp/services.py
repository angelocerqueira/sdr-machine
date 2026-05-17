"""DB services pro webhook handler: upsert idempotente + correlação lead/outreach.

Camada pura sobre SQLAlchemy. Sem HTTP, sem httpx. Cada função recebe
`db: Session` injetada pelo caller (handler ou router).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Lead
from app.whatsapp.normalizer import normalize_phone_br

logger = logging.getLogger(__name__)


def find_lead_by_phone(
    db: Session, workspace_id: int, normalized_phone: str
) -> Lead | None:
    """Acha lead cujo `telefone` (possivelmente mascarado no DB) normaliza
    pro mesmo valor de `normalized_phone`.

    Telefones no DB chegam em formatos heterogêneos ("(44) 99999-0000",
    "+55 44 9...", "44999990000"). LIKE em substring não bate em strings
    mascaradas, então iteramos leads não-nulos e normalizamos em Python.
    Single-tenant (workspace_id=1) hoje; em escala maior, adicionar
    coluna `telefone_normalizado` indexada.
    """
    if not normalized_phone or len(normalized_phone) < 9:
        return None
    candidates = (
        db.query(Lead)
        .filter(Lead.telefone.isnot(None))
        .filter(Lead.telefone != "")
        .order_by(Lead.id.asc())
        .all()
    )
    for lead in candidates:
        try:
            if normalize_phone_br(lead.telefone) == normalized_phone:
                return lead
        except ValueError:
            continue
    return None
