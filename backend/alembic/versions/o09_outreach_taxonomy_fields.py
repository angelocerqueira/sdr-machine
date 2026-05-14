"""add outreach taxonomy fields — cta_usado + angulo_usado

Revision ID: o09_outreach_taxonomy_fields
Revises: o08_outreach_quality_fields
Create Date: 2026-05-13

Adds taxonomy columns to outreach_messages so the generator can record which
copy ingredients were picked for a given message:
- cta_usado: identifier of the CTA chosen from config/ctas.json (e.g.
  'ver_landing', 'agendar_call'). Nullable — older rows pre-PR2 don't have it.
- angulo_usado: identifier of the angulo chosen from config/angulos.json
  (e.g. 'sem_site', 'site_lento'). Nullable.

Other outreach quality columns (variant_label, copy_count, click_count,
manual_rating, needs_review, tratamento_formal) ship in later PRs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o09_outreach_taxonomy_fields"
down_revision: Union[str, None] = "o08_outreach_quality_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_messages",
        sa.Column(
            "cta_usado",
            sa.String(length=40),
            nullable=True,
        ),
    )
    op.add_column(
        "outreach_messages",
        sa.Column(
            "angulo_usado",
            sa.String(length=40),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("outreach_messages", "angulo_usado")
    op.drop_column("outreach_messages", "cta_usado")
