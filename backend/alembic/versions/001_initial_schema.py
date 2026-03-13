"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("params", sa.JSON(), server_default="{}"),
        sa.Column("result_summary", sa.JSON(), server_default="{}"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("telefone", sa.String(50)),
        sa.Column("website", sa.String(500)),
        sa.Column("endereco", sa.String(500)),
        sa.Column("cidade", sa.String(100)),
        sa.Column("nicho", sa.String(100)),
        sa.Column("categoria", sa.String(100)),
        sa.Column("rating", sa.Numeric(2, 1)),
        sa.Column("reviews_count", sa.Integer(), server_default="0"),
        sa.Column("google_maps_url", sa.String(500)),
        sa.Column("top_reviews", sa.JSON(), server_default="[]"),
        sa.Column("status", sa.String(50), server_default="scraped"),
        sa.Column("opportunity_score", sa.Integer()),
        sa.Column("opportunity_reasons", sa.JSON(), server_default="[]"),
        sa.Column("site_analysis", sa.JSON(), server_default="{}"),
        sa.Column("lp_html", sa.Text()),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_leads_nicho", "leads", ["nicho"])
    op.create_index("idx_leads_cidade", "leads", ["cidade"])
    op.create_index("idx_leads_score", "leads", ["opportunity_score"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("whatsapp_link", sa.String(500)),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("response_received_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_outreach_messages_lead_id", "outreach_messages", ["lead_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER leads_updated_at
            BEFORE UPDATE ON leads
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS leads_updated_at ON leads")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at()")
    op.drop_table("outreach_messages")
    op.drop_table("leads")
    op.drop_table("jobs")
