"""backfill place_id from google_maps_url and add UNIQUE constraint

This migration is self-contained: it populates ``place_id`` for existing
rows using a regex extraction from ``google_maps_url`` BEFORE adding the
UNIQUE constraint. That way auto-deploy (``alembic upgrade head`` in the
Railway Dockerfile) does the right thing without needing a manual
backfill step between migrations.

Rows where no place_id can be extracted stay NULL — Postgres treats
multiple NULLs as distinct for UNIQUE, so that's allowed.

Revision ID: m06_place_id_unique
Revises: l05_cleanup_fields
Create Date: 2026-04-24 00:10:00
"""
from alembic import op


revision = "m06_place_id_unique"
down_revision = "l05_cleanup_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Backfill place_id from the canonical ``?query_place_id=...`` param.
    op.execute(
        """
        UPDATE leads
           SET place_id = substring(google_maps_url FROM 'query_place_id=([^&]+)')
         WHERE place_id IS NULL
           AND google_maps_url ~ 'query_place_id='
        """
    )
    # 2. Fallback: the embedded !1s<id> token used by some map URLs.
    op.execute(
        """
        UPDATE leads
           SET place_id = substring(google_maps_url FROM '!1s([^!]+)')
         WHERE place_id IS NULL
           AND google_maps_url ~ '!1s'
        """
    )
    # 3. Now enforce uniqueness — new scrapes rely on it.
    op.create_unique_constraint(
        "uq_leads_place_id",
        "leads",
        ["place_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_leads_place_id", "leads", type_="unique")
