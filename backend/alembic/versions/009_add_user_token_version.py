"""Add user token version

Revision ID: 009_add_user_token_version
Revises: 008_add_evaluation_runs
Create Date: 2026-07-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '009_add_user_token_version'
down_revision = '008_add_evaluation_runs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')