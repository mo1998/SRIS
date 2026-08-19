"""Organization evaluation settings

Revision ID: 021_add_organization_evaluation_settings
Revises: 020_add_password_reset_tokens
Create Date: 2026-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '021_add_organization_evaluation_settings'
down_revision = '020_add_password_reset_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("organizations")}

    if "evaluation_provider" not in columns:
        op.add_column("organizations", sa.Column("evaluation_provider", sa.String(length=50), nullable=True))
    if "evaluation_model" not in columns:
        op.add_column("organizations", sa.Column("evaluation_model", sa.String(length=255), nullable=True))
    if "evaluation_base_url" not in columns:
        op.add_column("organizations", sa.Column("evaluation_base_url", sa.String(length=500), nullable=True))
    if "evaluation_api_key" not in columns:
        op.add_column("organizations", sa.Column("evaluation_api_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "evaluation_api_key")
    op.drop_column("organizations", "evaluation_base_url")
    op.drop_column("organizations", "evaluation_model")
    op.drop_column("organizations", "evaluation_provider")