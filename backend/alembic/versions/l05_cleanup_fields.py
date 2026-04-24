"""add parent_lead_id, nome_limpo, place_id for base cleanup

Revision ID: l05_cleanup_fields
Revises: k04_classification
Create Date: 2026-04-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "l05_cleanup_fields"
down_revision = "k04_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "parent_lead_id",
            sa.Integer(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("leads", sa.Column("nome_limpo", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("place_id", sa.String(length=100), nullable=True))

    op.create_index("idx_leads_parent_lead_id", "leads", ["parent_lead_id"])
    op.create_index("idx_leads_place_id", "leads", ["place_id"])


def downgrade() -> None:
    op.drop_index("idx_leads_place_id", table_name="leads")
    op.drop_index("idx_leads_parent_lead_id", table_name="leads")
    op.drop_column("leads", "place_id")
    op.drop_column("leads", "nome_limpo")
    op.drop_column("leads", "parent_lead_id")
