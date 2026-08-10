"""Add integrity_events table

Revision ID: 016_add_integrity_events
Revises: 015_add_video_file_path
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '016_add_integrity_events'
down_revision = '015_add_video_file_path'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS integrity_events (id SERIAL PRIMARY KEY, response_id INTEGER NOT NULL, event_type VARCHAR(50) NOT NULL, details TEXT, created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, FOREIGN KEY(response_id) REFERENCES candidate_responses(id))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_integrity_events_response_id ON integrity_events (response_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_integrity_events_event_type ON integrity_events (event_type)")


def downgrade() -> None:
    op.drop_table('integrity_events')
