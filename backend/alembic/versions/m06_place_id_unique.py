"""add UNIQUE constraint on place_id

Depends on scripts.backfill_place_id having been executed first so existing
rows carry a place_id value (NULL rows are allowed by the partial uniqueness
semantics of the constraint).

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
    op.create_unique_constraint(
        "uq_leads_place_id",
        "leads",
        ["place_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_leads_place_id", "leads", type_="unique")
