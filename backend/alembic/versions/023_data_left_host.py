"""Record whether evaluation payloads left the host

Revision ID: 023_data_left_host
Revises: 022_evaluation_provider_presets
Create Date: 2026-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '023_data_left_host'
down_revision = '022_evaluation_provider_presets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("evaluation_runs")}

    if "data_left_host" not in columns:
        op.add_column("evaluation_runs", sa.Column("data_left_host", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_runs", "data_left_host")