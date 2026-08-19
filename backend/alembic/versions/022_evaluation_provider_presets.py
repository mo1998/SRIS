"""Organization evaluation provider presets

Revision ID: 022_evaluation_provider_presets
Revises: 021_organization_eval_settings
Create Date: 2026-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '022_evaluation_provider_presets'
down_revision = '021_organization_eval_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "evaluation_provider_presets" not in tables:
        op.create_table(
            "evaluation_provider_presets",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("organization_id", sa.Integer(), nullable=False, index=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model", sa.String(length=255), nullable=True),
            sa.Column("base_url", sa.String(length=500), nullable=True),
            sa.Column("api_key", sa.String(length=500), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    op.drop_table("evaluation_provider_presets")
