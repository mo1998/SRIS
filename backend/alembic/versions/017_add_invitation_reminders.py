"""Add invitation reminder fields

Revision ID: 017_add_invitation_reminders
Revises: 016_add_integrity_events
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '017_add_invitation_reminders'
down_revision = '016_add_integrity_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent + dialect-safe: SQLite does not support "ADD COLUMN IF NOT
    # EXISTS", so probe existing columns via the inspector instead.
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns('invitations')}
    if 'last_reminder_at' not in columns:
        op.add_column('invitations', sa.Column('last_reminder_at', sa.DateTime(), nullable=True))
    if 'reminder_count' not in columns:
        op.add_column('invitations', sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns('invitations')}
    if 'reminder_count' in columns:
        op.drop_column('invitations', 'reminder_count')
    if 'last_reminder_at' in columns:
        op.drop_column('invitations', 'last_reminder_at')
