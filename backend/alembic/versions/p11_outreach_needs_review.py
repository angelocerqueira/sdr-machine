"""add needs_review column to outreach_messages

Revision ID: p11_outreach_needs_review
Revises: p10_lead_tratamento_formal
Create Date: 2026-05-14

Adds a single column to ``outreach_messages`` carrying the "needs human
review" notification flag (PR4.3). Set to True at generation time when the
lead's nicho has a compliance config (regulated nichos: advocacia, medicina,
odontologia, contabilidade, arquitetura, engenharia). UI renders a badge
that the SDR can clear via POST /api/leads/{lead_id}/messages/{message_id}
/mark-reviewed.

- needs_review: Boolean, NOT NULL, server_default=false
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p11_outreach_needs_review"
down_revision: Union[str, None] = "p10_lead_tratamento_formal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_messages",
        sa.Column(
            "needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("outreach_messages", "needs_review")
