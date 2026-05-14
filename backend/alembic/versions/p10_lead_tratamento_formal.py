"""add tratamento_formal column to leads

Revision ID: p10_lead_tratamento_formal
Revises: o09_outreach_taxonomy_fields
Create Date: 2026-05-14

Adds a single column to `leads` capturing the inferred formal treatment
("voce" vs "senhor_a") to be used by the outreach generator. The actual
inference logic + tests land in the next PR (PR3.2).

- tratamento_formal: String(10), nullable. Indexed via
  idx_leads_tratamento_formal for filtering/segmentation.

Other deferred outreach quality columns (needs_review, copy_count,
click_count, manual_rating, variant_label) ship in later PRs (PR4/PR5).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p10_lead_tratamento_formal"
down_revision: Union[str, None] = "o09_outreach_taxonomy_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "tratamento_formal",
            sa.String(length=10),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_leads_tratamento_formal",
        "leads",
        ["tratamento_formal"],
    )


def downgrade() -> None:
    op.drop_index("idx_leads_tratamento_formal", table_name="leads")
    op.drop_column("leads", "tratamento_formal")
