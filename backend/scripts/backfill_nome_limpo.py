"""Populate `nome_limpo` by stripping Google keyword stuffing from `nome`.

Google Business Profile names often concatenate the brand with the niche
and city (e.g. "Madre Hair Cabeleireiros - Salão de beleza em Florianópolis").
The raw `nome` stays intact (preserved for matching); `nome_limpo` gets the
first segment before a separator — the brand name most customers would say.

Heuristic:
- Split on ` - `, ` | `, ` / ` or ` – ` (en-dash). Take the first segment.
- Trim whitespace. If the first segment is shorter than 3 chars, keep nome.
- Strip common city suffix " em <Cidade>" if it leaks.

Usage:
    python -m scripts.backfill_nome_limpo          # dry-run
    python -m scripts.backfill_nome_limpo --apply
    python -m scripts.backfill_nome_limpo --rerun  # overwrite existing
"""
from __future__ import annotations

import argparse
import re

from app.database import SessionLocal
from app.models import Lead


SEP_RE = re.compile(r"\s+[-|/–]\s+")
CITY_SUFFIX_RE = re.compile(r"\s+em\s+[A-ZÀ-Ý][^\s].*$", re.IGNORECASE)


def clean_name(nome: str | None) -> str | None:
    if not nome:
        return None
    parts = SEP_RE.split(nome, maxsplit=1)
    first = parts[0].strip()
    if len(first) < 3:
        first = nome.strip()
    first = CITY_SUFFIX_RE.sub("", first).strip()
    return first or nome.strip()


def run(apply: bool, rerun: bool) -> int:
    db = SessionLocal()
    changed = 0
    try:
        q = db.query(Lead)
        if not rerun:
            q = q.filter(Lead.nome_limpo.is_(None))
        leads = q.order_by(Lead.id.asc()).all()
        for lead in leads:
            cleaned = clean_name(lead.nome)
            if cleaned and cleaned != lead.nome_limpo:
                if lead.nome and cleaned != lead.nome:
                    print(f"  #{lead.id:5d}  {lead.nome[:55]:55} → {cleaned}")
                lead.nome_limpo = cleaned
                changed += 1

        if apply:
            db.commit()
            print(f"\nCOMMIT: {changed} leads atualizados.")
        else:
            db.rollback()
            print(f"\nDRY RUN: {changed} leads seriam alterados. Use --apply.")
        return changed
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--rerun", action="store_true")
    args = p.parse_args()
    run(apply=args.apply, rerun=args.rerun)
