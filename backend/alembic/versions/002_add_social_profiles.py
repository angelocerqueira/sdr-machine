"""add social_profiles to leads

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("social_profiles", sa.JSON(), server_default=sa.text("'{}'"), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "social_profiles")
