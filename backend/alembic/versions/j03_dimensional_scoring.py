"""dimensional scoring — add 4 score axes + nivel_recomendado to leads

Revision ID: j03
Revises: i02_smart_enrichment_fields
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "j03"
down_revision = "i02_smart_enrichment_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("score_acessibilidade", sa.Integer(), server_default="0", nullable=False))
    op.add_column("leads", sa.Column("score_lp", sa.Integer(), server_default="0", nullable=False))
    op.add_column("leads", sa.Column("score_automacao", sa.Integer(), server_default="0", nullable=False))
    op.add_column("leads", sa.Column("score_mapa", sa.Integer(), server_default="0", nullable=False))
    op.add_column("leads", sa.Column("nivel_recomendado", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "nivel_recomendado")
    op.drop_column("leads", "score_mapa")
    op.drop_column("leads", "score_automacao")
    op.drop_column("leads", "score_lp")
    op.drop_column("leads", "score_acessibilidade")
