"""Move social URLs stored in `website` into structured `social_profiles`.

~20% of the base had Instagram/Facebook/WhatsApp links stored as website,
which inflates the "has site" signal and prevents the scoring from marking
them as `sem_site` (max opportunity).

For each affected lead:
- parses the URL and routes it into `social_profiles[platform]`;
- merges non-destructively with any existing social_profiles entry;
- sets `has_instagram=True` when applicable;
- fills `telefone` from `wa.me/<phone>` when the lead has no phone yet;
- finally sets `website = NULL`.

Usage:
    python -m scripts.reclassify_social_as_site          # dry-run
    python -m scripts.reclassify_social_as_site --apply  # commit
"""
from __future__ import annotations

import re
import sys
from urllib.parse import urlparse

from app.database import SessionLocal
from app.models import Lead


SOCIAL_HOSTS = (
    "instagram.com",
    "facebook.com",
    "fb.com",
    "wa.me",
    "api.whatsapp.com",
    "linktr.ee",
    "biolink",
    "linkin.bio",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
)


def classify(url: str) -> tuple[str, dict] | None:
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except Exception:
        return None
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.strip("/")

    if "instagram.com" in host:
        username = path.split("/")[0] if path else None
        data = {"url": url}
        if username:
            data["username"] = username
        return "instagram", data

    if "facebook.com" in host or "fb.com" in host:
        handle = path.split("/")[0] if path else None
        data = {"url": url}
        if handle:
            data["handle"] = handle
        return "facebook", data

    if "wa.me" in host or "api.whatsapp.com" in host:
        phone = re.sub(r"\D", "", path) or None
        data = {"url": url}
        if phone:
            data["phone"] = phone
        return "whatsapp", data

    if "linktr.ee" in host or "biolink" in host or "linkin.bio" in host:
        return "link_in_bio", {"url": url}

    if "tiktok.com" in host:
        return "tiktok", {"url": url}

    if "youtube.com" in host or "youtu.be" in host:
        return "youtube", {"url": url}

    return None


def is_social(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return any(h in low for h in SOCIAL_HOSTS)


def run(dry_run: bool = True) -> int:
    db = SessionLocal()
    affected = 0
    try:
        leads = db.query(Lead).filter(Lead.website.isnot(None)).all()
        for lead in leads:
            if not is_social(lead.website):
                continue
            result = classify(lead.website)
            if not result:
                continue

            platform, data = result
            social = dict(lead.social_profiles or {})
            existing = social.get(platform) or {}
            existing = existing if isinstance(existing, dict) else {}
            merged = {**data, **{k: v for k, v in existing.items() if v}}
            social[platform] = merged

            if platform == "whatsapp" and not lead.telefone and data.get("phone"):
                lead.telefone = f"+{data['phone']}"
            if platform == "instagram":
                lead.has_instagram = True

            lead.social_profiles = social
            lead.website = None
            affected += 1
            print(f"  #{lead.id:5d} {(lead.nome or '')[:45]:45} → {platform}")

        if dry_run:
            print(f"\nDRY RUN: {affected} leads afetados. Use --apply pra commitar.")
            db.rollback()
        else:
            db.commit()
            print(f"\nCOMMIT: {affected} leads atualizados.")
    finally:
        db.close()
    return affected


if __name__ == "__main__":
    run(dry_run="--apply" not in sys.argv)
