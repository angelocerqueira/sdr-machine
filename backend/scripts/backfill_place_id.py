"""Backfill `place_id` column from google_maps_url.

Redundant in the happy path — migration m06 does the same backfill via SQL
before creating the UNIQUE constraint. Keep this script around for:
- debugging / inspecting which rows have no parseable place_id;
- re-running with the Python regex after manual edits to google_maps_url.

Usage:
    python -m scripts.backfill_place_id          # dry-run
    python -m scripts.backfill_place_id --apply
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models import Lead
from app.pipeline.scraper import extract_place_id


def run(apply: bool) -> int:
    db = SessionLocal()
    updated = 0
    missing = 0
    try:
        leads = db.query(Lead).filter(Lead.place_id.is_(None)).all()
        for lead in leads:
            pid = extract_place_id(lead.google_maps_url)
            if pid:
                lead.place_id = pid
                updated += 1
            else:
                missing += 1
                print(f"  #{lead.id:5d} {(lead.nome or '')[:40]}  sem place_id no URL")

        if apply:
            db.commit()
            print(f"\nCOMMIT: {updated} com place_id, {missing} sem.")
        else:
            db.rollback()
            print(f"\nDRY RUN: {updated} seriam atualizados, {missing} sem place_id.")
        return updated
    finally:
        db.close()


if __name__ == "__main__":
    run(apply="--apply" in sys.argv)
