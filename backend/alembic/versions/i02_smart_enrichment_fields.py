"""add smart enrichment fields to leads

Revision ID: i02_smart_enrichment_fields
Revises: h01_better_auth
Create Date: 2026-04-10 12:00:00.000000

Adds new columns to support the Smart Enrichment Pipeline:
- Contact: email
- Company registry (CNPJ / BrasilAPI): cnpj, razao_social, porte, cnae,
  data_fundacao, socios
- Website tech: tech_stack
- Provider audit trail: enrichment_sources
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i02_smart_enrichment_fields"
down_revision: Union[str, None] = "h01_better_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("cnpj", sa.String(length=18), nullable=True))
    op.add_column("leads", sa.Column("razao_social", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("porte", sa.String(length=50), nullable=True))
    op.add_column("leads", sa.Column("cnae", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("data_fundacao", sa.Date(), nullable=True))
    op.add_column(
        "leads",
        sa.Column("socios", sa.JSON(), nullable=True, server_default="[]"),
    )
    op.add_column(
        "leads",
        sa.Column("tech_stack", sa.JSON(), nullable=True, server_default="[]"),
    )
    op.add_column(
        "leads",
        sa.Column("enrichment_sources", sa.JSON(), nullable=True, server_default="[]"),
    )
    op.create_index("idx_leads_email", "leads", ["email"])
    op.create_index("idx_leads_cnpj", "leads", ["cnpj"])


def downgrade() -> None:
    op.drop_index("idx_leads_cnpj", table_name="leads")
    op.drop_index("idx_leads_email", table_name="leads")
    op.drop_column("leads", "enrichment_sources")
    op.drop_column("leads", "tech_stack")
    op.drop_column("leads", "socios")
    op.drop_column("leads", "data_fundacao")
    op.drop_column("leads", "cnae")
    op.drop_column("leads", "porte")
    op.drop_column("leads", "razao_social")
    op.drop_column("leads", "cnpj")
    op.drop_column("leads", "email")
