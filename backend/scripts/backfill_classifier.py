"""Run ONLY the classifier on existing enriched leads (no re-score).

Runs the ClassificationProvider directly (not through the orchestrator) so
existing opportunity_score, site_analysis and other enrichment fields are
preserved. Populates: perfil_lead, nicho_canonico, nicho_source,
nicho_confidence, pacote_sugerido, prioridade, classification_hash,
classified_at.

Usage:
    python -m scripts.backfill_classifier              # dry-run, all missing
    python -m scripts.backfill_classifier --apply
    python -m scripts.backfill_classifier --rerun      # reclassify everyone
    python -m scripts.backfill_classifier --ids 1,2,3
    python -m scripts.backfill_classifier --limit 50
"""
from __future__ import annotations

import argparse
from datetime import datetime

from app.database import SessionLocal
from app.models import Lead
from app.pipeline.enrichment.base_provider import EnrichmentContext
from app.pipeline.enrichment.classifier import build_classifier_llm_client
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)


CLASSIFICATION_FIELDS = (
    "perfil_lead",
    "nicho_canonico",
    "nicho_source",
    "nicho_confidence",
    "pacote_sugerido",
    "prioridade",
    "classification_hash",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--rerun", action="store_true", help="reclassify even if already classified")
    p.add_argument("--ids", default=None)
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def select_leads(db, args) -> list[Lead]:
    q = db.query(Lead)
    if args.ids:
        ids = [int(x) for x in args.ids.split(",") if x.strip()]
        q = q.filter(Lead.id.in_(ids))
    elif not args.rerun:
        q = q.filter(Lead.classified_at.is_(None))
    q = q.order_by(Lead.id.asc())
    if args.limit:
        q = q.limit(args.limit)
    return q.all()


def run(args: argparse.Namespace) -> int:
    provider = ClassificationProvider(llm_client=build_classifier_llm_client())
    db = SessionLocal()
    ok, skipped, failed = 0, 0, 0
    try:
        leads = select_leads(db, args)
        print(f"classifier backfill  dry_run={not args.apply}  leads={len(leads)}\n")

        for idx, lead in enumerate(leads, 1):
            prefix = f"[{idx}/{len(leads)}] #{lead.id:5d} {(lead.nome or '')[:40]:40}"
            context = EnrichmentContext()
            context.computed_score = lead.opportunity_score

            try:
                result = provider.run(lead, context)
                if not result.success:
                    skipped += 1
                    print(f"{prefix}  SKIP: {'; '.join(result.errors)[:80]}")
                    continue

                data = result.data or {}
                for attr in CLASSIFICATION_FIELDS:
                    if attr in data and data[attr] is not None:
                        setattr(lead, attr, data[attr])
                if data.get("perfil_lead") is not None:
                    lead.classified_at = datetime.utcnow()

                if args.apply:
                    db.commit()
                else:
                    db.rollback()
                ok += 1
                print(
                    f"{prefix}  perfil={data.get('perfil_lead') or '-':20}"
                    f"  nicho={data.get('nicho_canonico') or '-':15}"
                    f"  pacote={data.get('pacote_sugerido') or '-'}"
                )
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"{prefix}  ERROR: {exc}")
    finally:
        db.close()

    action = "COMMIT" if args.apply else "DRY RUN"
    print(f"\n{action}: ok={ok} skipped={skipped} failed={failed}")
    return ok


if __name__ == "__main__":
    run(parse_args())
