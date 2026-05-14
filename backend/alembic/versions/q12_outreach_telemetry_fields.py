"""q12_outreach_telemetry_fields — telemetry + A/B (PR5.1)

Adds copy_count, click_count, manual_rating, variant_label.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q12_outreach_telemetry_fields"
down_revision: Union[str, None] = "p11_outreach_needs_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_messages",
        sa.Column("copy_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("manual_rating", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("variant_label", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outreach_messages", "variant_label")
    op.drop_column("outreach_messages", "manual_rating")
    op.drop_column("outreach_messages", "click_count")
    op.drop_column("outreach_messages", "copy_count")
