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
    op.execute("ALTER TABLE invitations ADD COLUMN IF NOT EXISTS last_reminder_at TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE invitations ADD COLUMN IF NOT EXISTS reminder_count INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE invitations DROP COLUMN IF EXISTS reminder_count")
    op.execute("ALTER TABLE invitations DROP COLUMN IF EXISTS last_reminder_at")
