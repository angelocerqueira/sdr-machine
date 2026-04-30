"""workspace settings — integrations, profile, targeting

Revision ID: n07
Revises: m06_place_id_unique
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "n07"
down_revision = "m06_place_id_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
    )
    op.create_index("idx_integration_settings_workspace", "integration_settings", ["workspace_id"])

    op.create_table(
        "workspace_profile",
        sa.Column("workspace_id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column("your_name", sa.String(length=255), nullable=True),
        sa.Column("your_email", sa.String(length=255), nullable=True),
        sa.Column("your_whatsapp", sa.String(length=50), nullable=True),
        sa.Column("your_website", sa.String(length=500), nullable=True),
        sa.Column("legal_basis", sa.String(length=64), nullable=True,
                  server_default="legitimo_interesse_b2b"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "workspace_targeting",
        sa.Column("workspace_id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("target_niches", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("target_cities", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("min_rating", sa.Float(), nullable=True),
        sa.Column("max_results_per_search", sa.Integer(), nullable=True),
        sa.Column("opportunity_score_threshold", sa.Integer(), nullable=True),
        sa.Column("diagnostic_model", sa.String(length=64), nullable=True),
        sa.Column("skip_ai_diagnostic", sa.Boolean(), nullable=True),
        sa.Column("skip_social_scraping", sa.Boolean(), nullable=True),
        sa.Column("ai_potential_threshold", sa.Integer(), nullable=True),
        sa.Column("disqualify_threshold", sa.Integer(), nullable=True),
        sa.Column("skip_service_level_analysis", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("workspace_targeting")
    op.drop_table("workspace_profile")
    op.drop_index("idx_integration_settings_workspace", table_name="integration_settings")
    op.drop_table("integration_settings")
