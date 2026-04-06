"""add public_id to leads

Revision ID: d778e8bac0db
Revises: 002
Create Date: 2026-04-06 04:16:34.003356
"""
import secrets
import string
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd778e8bac0db'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALPHABET = string.ascii_letters + string.digits + "-_"


def _nanoid(size: int = 16) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(size))


def upgrade() -> None:
    # 1. Add column as nullable
    op.add_column('leads', sa.Column('public_id', sa.String(length=16), nullable=True))

    # 2. Backfill existing rows
    conn = op.get_bind()
    leads = conn.execute(sa.text("SELECT id FROM leads WHERE public_id IS NULL")).fetchall()
    for (lead_id,) in leads:
        conn.execute(
            sa.text("UPDATE leads SET public_id = :pid WHERE id = :id"),
            {"pid": _nanoid(), "id": lead_id},
        )

    # 3. Set NOT NULL and unique constraint
    op.alter_column('leads', 'public_id', nullable=False)
    op.create_unique_constraint('uq_leads_public_id', 'leads', ['public_id'])


def downgrade() -> None:
    op.drop_constraint('uq_leads_public_id', 'leads', type_='unique')
    op.drop_column('leads', 'public_id')
