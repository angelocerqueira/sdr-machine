"""Fix leads from job 13 whose `nicho` was stored as a raw list.

Job 13 ingested 10 leads with `nicho = "Saude, advogados, construção,
logística, agronegocio"` (user typed a list instead of a single niche).
All 10 returned Google categories are advocacia-related (Escritório de
advocacia, Advogado, etc.), so we normalize the field to "advogados".

Usage:
    python -m scripts.fix_job_13_nicho          # dry-run
    python -m scripts.fix_job_13_nicho --apply
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models import Lead


BAD_NICHO = "Saude, advogados, construção, logística, agronegocio"
NEW_NICHO = "advogados"


def run(dry_run: bool = True) -> int:
    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(Lead.nicho == BAD_NICHO).all()
        for lead in leads:
            print(f"  #{lead.id:5d} job={lead.job_id} {(lead.nome or '')[:50]}")
            lead.nicho = NEW_NICHO

        if dry_run:
            print(f"\nDRY RUN: {len(leads)} leads afetados. Use --apply pra commitar.")
            db.rollback()
        else:
            db.commit()
            print(f"\nCOMMIT: {len(leads)} leads atualizados.")
        return len(leads)
    finally:
        db.close()


if __name__ == "__main__":
    run(dry_run="--apply" not in sys.argv)
