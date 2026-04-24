"""Detect multi-unit businesses (filiais) and link them via parent_lead_id.

Strategy:
- Group by normalized website (stripping trailing slashes, scheme, www).
- Group by cnpj when present.
- Ignore social URLs (already moved out by reclassify_social_as_site).
- In each group with >1 lead, the lead with the smallest id becomes the
  parent. Every other lead in the group gets `parent_lead_id = parent.id`.
- Idempotent: leads already pointing to the correct parent are skipped.

Run once after social-as-site cleanup (website-based), and again after CNPJ
enrichment (cnpj-based picks up filiais that share an umbrella company).

Usage:
    python -m scripts.detect_filiais              # dry-run, both keys
    python -m scripts.detect_filiais --apply
    python -m scripts.detect_filiais --key=cnpj   # only cnpj grouping
    python -m scripts.detect_filiais --key=website
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

from app.database import SessionLocal
from app.models import Lead


SOCIAL_HOSTS = (
    "instagram.com",
    "facebook.com",
    "fb.com",
    "wa.me",
    "linktr.ee",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
)


def normalize_website(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except Exception:
        return None
    host = parsed.netloc.lower().removeprefix("www.")
    if not host or any(s in host for s in SOCIAL_HOSTS):
        return None
    path = parsed.path.rstrip("/")
    return f"{host}{path}" if path else host


def normalize_cnpj(cnpj: str | None) -> str | None:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    return digits if len(digits) == 14 else None


def group_leads(leads: list[Lead], key_name: str) -> dict[str, list[Lead]]:
    groups: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        if key_name == "website":
            k = normalize_website(lead.website)
        elif key_name == "cnpj":
            k = normalize_cnpj(lead.cnpj)
        else:
            k = None
        if k:
            groups[k].append(lead)
    return {k: v for k, v in groups.items() if len(v) > 1}


def link_group(group: list[Lead]) -> list[tuple[Lead, int]]:
    group_sorted = sorted(group, key=lambda x: x.id)
    parent = group_sorted[0]
    changes = []
    for child in group_sorted[1:]:
        if child.parent_lead_id != parent.id and child.id != parent.id:
            changes.append((child, parent.id))
    return changes


def run(dry_run: bool = True, keys: list[str] | None = None) -> int:
    keys = keys or ["website", "cnpj"]
    db = SessionLocal()
    total = 0
    try:
        leads = db.query(Lead).all()
        for key in keys:
            groups = group_leads(leads, key)
            if not groups:
                print(f"[{key}] nenhum grupo de filiais encontrado.")
                continue
            print(f"\n[{key}] {len(groups)} grupos de filiais:")
            for k, group in groups.items():
                changes = link_group(group)
                parent = sorted(group, key=lambda x: x.id)[0]
                print(f"  {k}  parent=#{parent.id} ({(parent.nome or '')[:40]})  filiais={len(changes)}")
                for child, parent_id in changes:
                    print(f"    ↳ #{child.id} {(child.nome or '')[:40]}")
                    child.parent_lead_id = parent_id
                    total += 1

        if dry_run:
            print(f"\nDRY RUN: {total} vínculos de filial. Use --apply pra commitar.")
            db.rollback()
        else:
            db.commit()
            print(f"\nCOMMIT: {total} filiais vinculadas.")
        return total
    finally:
        db.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    apply = "--apply" in args
    keys = None
    for a in args:
        if a.startswith("--key="):
            keys = [a.split("=", 1)[1]]
    run(dry_run=not apply, keys=keys)
