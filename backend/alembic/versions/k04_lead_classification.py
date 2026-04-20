"""add lead classification fields

Revision ID: k04_classification
Revises: j03
Create Date: 2026-04-20 00:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "k04_classification"
down_revision = "j03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("perfil_lead", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_canonico", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_source", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_confidence", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("pacote_sugerido", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("prioridade", sa.String(length=20), nullable=True))
    op.add_column("leads", sa.Column("classification_hash", sa.String(length=32), nullable=True))
    op.add_column("leads", sa.Column("classified_at", sa.DateTime(), nullable=True))
    op.add_column("leads", sa.Column("has_instagram", sa.Boolean(), nullable=True))

    op.create_index("idx_leads_perfil_lead", "leads", ["perfil_lead"])
    op.create_index("idx_leads_nicho_canonico", "leads", ["nicho_canonico"])
    op.create_index("idx_leads_pacote_sugerido", "leads", ["pacote_sugerido"])
    op.create_index("idx_leads_prioridade", "leads", ["prioridade"])


def downgrade() -> None:
    op.drop_index("idx_leads_prioridade", table_name="leads")
    op.drop_index("idx_leads_pacote_sugerido", table_name="leads")
    op.drop_index("idx_leads_nicho_canonico", table_name="leads")
    op.drop_index("idx_leads_perfil_lead", table_name="leads")
    op.drop_column("leads", "has_instagram")
    op.drop_column("leads", "classified_at")
    op.drop_column("leads", "classification_hash")
    op.drop_column("leads", "prioridade")
    op.drop_column("leads", "pacote_sugerido")
    op.drop_column("leads", "nicho_confidence")
    op.drop_column("leads", "nicho_source")
    op.drop_column("leads", "nicho_canonico")
    op.drop_column("leads", "perfil_lead")
