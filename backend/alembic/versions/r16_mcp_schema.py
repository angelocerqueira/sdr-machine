"""mcp schema: mcp_tokens + pending_actions

Revision ID: r16_mcp_schema
Revises: r13_whatsapp_inbox_schema
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = "r16_mcp_schema"
down_revision = "r13_whatsapp_inbox_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(80), nullable=False, unique=True),
        sa.Column("last4", sa.String(4), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime),
        sa.Column("revoked_at", sa.DateTime),
    )
    op.create_index("ix_mcp_tokens_hash", "mcp_tokens", ["token_hash"], unique=True)
    op.create_index("ix_mcp_tokens_workspace", "mcp_tokens", ["workspace_id"])

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("workspace_id", sa.Integer, nullable=False, server_default="1"),
        sa.Column("action_type", sa.String(60), nullable=False),
        sa.Column("params", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("preview", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_token_hash", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("committed_at", sa.DateTime),
        sa.Column("cancelled_at", sa.DateTime),
        sa.Column("result", sa.JSON),
    )
    op.create_index("ix_pending_actions_expires", "pending_actions", ["expires_at"])
    op.create_index("ix_pending_actions_workspace", "pending_actions", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_actions_workspace", table_name="pending_actions")
    op.drop_index("ix_pending_actions_expires", table_name="pending_actions")
    op.drop_table("pending_actions")
    op.drop_index("ix_mcp_tokens_workspace", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_hash", table_name="mcp_tokens")
    op.drop_table("mcp_tokens")
