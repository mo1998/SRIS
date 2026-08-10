"""Add invitation reminder fields

Revision ID: 017_add_invitation_reminders
Revises: 016_add_integrity_events
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '017_add_invitation_reminders'
down_revision = '016_add_integrity_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invitations', sa.Column('last_reminder_at', sa.DateTime(), nullable=True))
    op.add_column('invitations', sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('invitations', 'reminder_count')
    op.drop_column('invitations', 'last_reminder_at')
