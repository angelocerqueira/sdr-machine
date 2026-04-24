"""Run the enrichment orchestrator over existing leads (backfill).

Two modes via flags:
- default (free tier): `--skip-paid` skips EmailDiscoverer and Apollo; runs
  CnpjProvider, WebsiteCrawler, SchemaOrg, TechStack, Classification.
- `--paid-only`: forces EmailDiscoverer + Apollo, skips everything else.
  Useful to run Hunter/Apollo only on HOT leads after free backfill.

Filters:
- `--hot-only`          only leads with opportunity_score >= 80
- `--min-score N`       only leads with score >= N
- `--status STATUS`     filter by status (default: any)
- `--missing-cnpj`      only leads without cnpj
- `--missing-classification`  only leads without classified_at
- `--ids 1,2,3`         explicit list
- `--limit N`           cap total leads

Execution:
- `--apply` to persist. Without it, it's a dry-run report.
- Commits after each lead (like the background job).
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Lead
from app.pipeline.enricher import enrich_lead_via_orchestrator
from app.pipeline.enrichment.apply import apply_enrichment_result


FREE_SKIP = ["email_discoverer", "apollo"]
PAID_FORCE = ["email_discoverer", "apollo"]
PAID_SKIP = [
    "cnpj_enricher",
    "website_crawler",
    "schema_extractor",
    "tech_stack",
    "classification",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit changes")
    parser.add_argument("--skip-paid", action="store_true", help="skip Hunter/Apollo")
    parser.add_argument("--paid-only", action="store_true", help="only run Hunter+Apollo")
    parser.add_argument("--hot-only", action="store_true")
    parser.add_argument("--min-score", type=int, default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--missing-cnpj", action="store_true")
    parser.add_argument("--missing-classification", action="store_true")
    parser.add_argument("--ids", default=None, help="comma-separated lead ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0, help="seconds between leads")
    return parser.parse_args()


def select_leads(db: Session, args: argparse.Namespace) -> list[Lead]:
    q = db.query(Lead)
    if args.ids:
        ids = [int(x) for x in args.ids.split(",") if x.strip()]
        q = q.filter(Lead.id.in_(ids))
    if args.status:
        q = q.filter(Lead.status == args.status)
    if args.hot_only:
        q = q.filter(Lead.opportunity_score >= 80)
    elif args.min_score is not None:
        q = q.filter(Lead.opportunity_score >= args.min_score)
    if args.missing_cnpj:
        q = q.filter((Lead.cnpj.is_(None)) | (Lead.cnpj == ""))
    if args.missing_classification:
        q = q.filter(Lead.classified_at.is_(None))
    q = q.order_by(Lead.id.asc())
    if args.limit:
        q = q.limit(args.limit)
    return q.all()


def run(args: argparse.Namespace) -> int:
    if args.skip_paid and args.paid_only:
        raise SystemExit("escolha --skip-paid OU --paid-only, não ambos")

    if args.paid_only:
        skip_providers = PAID_SKIP
        force_providers = PAID_FORCE
        mode = "paid-only"
    elif args.skip_paid:
        skip_providers = list(FREE_SKIP)
        force_providers = ["cnpj_enricher", "schema_extractor", "tech_stack"]
        mode = "free-tier"
    else:
        skip_providers = []
        force_providers = []
        mode = "full"

    db = SessionLocal()
    ok, failed = 0, 0
    try:
        leads = select_leads(db, args)
        print(f"mode={mode}  dry_run={not args.apply}  leads={len(leads)}")
        print(f"skip={skip_providers}  force={force_providers}\n")

        for idx, lead in enumerate(leads, 1):
            prefix = f"[{idx}/{len(leads)}] #{lead.id:5d} {(lead.nome or '')[:40]:40}"
            try:
                result = enrich_lead_via_orchestrator(
                    lead,
                    skip_providers=skip_providers,
                    force_providers=force_providers,
                )
                apply_enrichment_result(lead, result)
                if lead.status == "scraped":
                    lead.status = "enriched"
                if args.apply:
                    db.commit()
                else:
                    db.rollback()
                ok += 1
                print(
                    f"{prefix}  score={result.get('opportunity_score')}"
                    f"  cnpj={'✓' if result.get('cnpj') else '-'}"
                    f"  email={'✓' if result.get('email') else '-'}"
                    f"  perfil={result.get('perfil_lead') or '-'}"
                )
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"{prefix}  ERROR: {exc}")
                if "--traceback" in sys.argv:
                    traceback.print_exc()

            if args.sleep:
                time.sleep(args.sleep)
    finally:
        db.close()

    action = "COMMIT" if args.apply else "DRY RUN"
    print(f"\n{action}: ok={ok} failed={failed}")
    return ok


if __name__ == "__main__":
    run(parse_args())
