"""add outreach quality fields — status + validation_errors

Revision ID: o08_outreach_quality_fields
Revises: n07
Create Date: 2026-05-13

Adds minimal columns to support the outreach quality overhaul lifecycle:
- status: lifecycle state of an outreach message (e.g. 'pronta',
  'rejeitada_validacao', 'aprovada', 'enviada'). NOT NULL, default 'pronta'
  so existing rows backfill cleanly.
- validation_errors: JSONB list of validator error keys (e.g.
  ['HARD_NO_NICHO', 'HARD_REGEN_LIMIT']). Nullable.

Other outreach quality columns (angulo_usado, cta_usado, variant_label,
copy_count, click_count, manual_rating, needs_review, tratamento_formal)
ship in later PRs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "o08_outreach_quality_fields"
down_revision: Union[str, None] = "n07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_messages",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pronta",
        ),
    )
    op.add_column(
        "outreach_messages",
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("outreach_messages", "validation_errors")
    op.drop_column("outreach_messages", "status")
