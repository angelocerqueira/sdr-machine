"""add landing_pages table

Revision ID: ac46f4e3f51d
Revises: d778e8bac0db
Create Date: 2026-04-06 04:25:06.867983
"""
import secrets
import string
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ac46f4e3f51d'
down_revision: Union[str, None] = 'd778e8bac0db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALPHABET = string.ascii_letters + string.digits + "-_"


def _nanoid(size: int = 16) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(size))


def upgrade() -> None:
    op.create_table('landing_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=16), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('html', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id')
    )
    op.create_index('idx_landing_pages_lead_id', 'landing_pages', ['lead_id'], unique=False)

    # Migrate existing lp_html data
    conn = op.get_bind()
    leads = conn.execute(
        sa.text("SELECT id, lp_html FROM leads WHERE lp_html IS NOT NULL AND lp_html != ''")
    ).fetchall()
    for lead_id, html in leads:
        conn.execute(
            sa.text(
                "INSERT INTO landing_pages (public_id, lead_id, html, version, is_active, created_at) "
                "VALUES (:pid, :lid, :html, 1, true, NOW())"
            ),
            {"pid": _nanoid(), "lid": lead_id, "html": html},
        )


def downgrade() -> None:
    # Copy active LP HTML back to leads
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE leads SET lp_html = lp.html "
        "FROM landing_pages lp WHERE lp.lead_id = leads.id AND lp.is_active = true"
    ))
    op.drop_index('idx_landing_pages_lead_id', table_name='landing_pages')
    op.drop_table('landing_pages')
