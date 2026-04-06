"""add unique constraint on landing_pages (lead_id, version)

Revision ID: g83b1a4d7e02
Revises: f21a8f592e69
Create Date: 2026-04-06 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'g83b1a4d7e02'
down_revision: Union[str, None] = 'f21a8f592e69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_landing_pages_lead_version', 'landing_pages', ['lead_id', 'version']
    )


def downgrade() -> None:
    op.drop_constraint('uq_landing_pages_lead_version', 'landing_pages', type_='unique')
