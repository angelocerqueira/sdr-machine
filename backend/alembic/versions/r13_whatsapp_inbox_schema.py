"""r13_whatsapp_inbox_schema — tabelas conversations + conversation_messages + colunas WhatsApp (P0 Inbox)

Spec: docs/superpowers/specs/2026-05-16-whatsapp-inbox-design.md §3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r13_whatsapp_inbox_schema"
down_revision: Union[str, None] = "q12_outreach_telemetry_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "lead_id",
            sa.Integer(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_chat_id", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "provider", "provider_chat_id",
            name="uq_conversations_workspace_provider_chat",
        ),
    )
    op.create_index("ix_conversations_lead_id", "conversations", ["lead_id"])
    op.create_index("ix_conversations_phone", "conversations", ["phone"])

    # --- conversation_messages ---
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=4), nullable=False),  # "in" | "out"
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by_user_id", sa.String(length=64), nullable=True),
        sa.Column(
            "outreach_message_id",
            sa.Integer(),
            sa.ForeignKey("outreach_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider_message_id", name="uq_conversation_messages_provider_msg_id"),
    )
    op.create_index(
        "ix_conversation_messages_conv_created",
        "conversation_messages",
        ["conversation_id", "created_at"],
    )

    # --- outreach_messages: novas colunas ---
    op.add_column(
        "outreach_messages",
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outreach_messages",
        sa.Column("failed_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_outreach_messages_provider_msg_id",
        "outreach_messages",
        ["provider_message_id"],
    )

    # --- leads: responded_at ---
    op.add_column(
        "leads",
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "responded_at")
    op.drop_index("ix_outreach_messages_provider_msg_id", table_name="outreach_messages")
    op.drop_column("outreach_messages", "failed_reason")
    op.drop_column("outreach_messages", "read_at")
    op.drop_column("outreach_messages", "delivered_at")
    op.drop_column("outreach_messages", "provider_message_id")
    op.drop_index("ix_conversation_messages_conv_created", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_phone", table_name="conversations")
    op.drop_index("ix_conversations_lead_id", table_name="conversations")
    op.drop_table("conversations")
