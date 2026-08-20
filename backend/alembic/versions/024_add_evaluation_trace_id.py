"""Add trace_id to evaluation runs

Revision ID: 024_add_evaluation_trace_id
Revises: 023_data_left_host
Create Date: 2026-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '024_add_evaluation_trace_id'
down_revision = '023_data_left_host'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("evaluation_runs")}

    if "trace_id" not in columns:
        op.add_column("evaluation_runs", sa.Column("trace_id", sa.String(length=100), nullable=True))
        op.create_index("ix_evaluation_runs_trace_id", "evaluation_runs", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_trace_id", table_name="evaluation_runs")
    op.drop_column("evaluation_runs", "trace_id")